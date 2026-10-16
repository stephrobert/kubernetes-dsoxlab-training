"""test_functional.py : ckad-pod-resources-labels

Ces tests lisent l'état du CLUSTER et du CONTENEUR, jamais les commandes
tapées.

Quatre affirmations. Les trois premières lisent la définition du Pod ; la
dernière entre dans chaque conteneur pour lire la limite de mémoire que le
noyau applique réellement, dans le cgroup. C'est elle qui prouve que les
resources déclarées ne sont pas qu'un texte.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "multi-app"
ATTENDU = {
    "web": {"requests": {"cpu": "100m", "memory": "64Mi"}, "limits": {"cpu": "200m", "memory": "128Mi"}},
    "logger": {"requests": {"cpu": "50m", "memory": "32Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
}
LIMITES_OCTETS = {"web": 128 * 1024 * 1024, "logger": 64 * 1024 * 1024}
LABELS = {"app": "multi-app", "tier": "frontend", "version": "v1"}
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, message(
        en=f"No Pod {POD} in {NAMESPACE}.",
        fr=f"Aucun Pod {POD} dans {NAMESPACE}.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Deux conteneurs, et le Pod tourne.
# ----------------------------------------------------------------------
def test_deux_conteneurs_en_marche(host):
    pod = {}
    for _ in range(12):
        pod = _pod(host)
        if pod["status"].get("phase") == "Running":
            break
        time.sleep(5)
    noms = [c["name"] for c in pod["spec"]["containers"]]
    assert sorted(noms) == ["logger", "web"], message(
        en=f"The Pod carries containers {noms}: web and logger expected, and nothing else.",
        fr=f"Le Pod porte les conteneurs {noms} : attendus web et logger, et rien d'autre.",
    )
    statuts = {s["name"]: s for s in pod["status"].get("containerStatuses") or []}
    pas_prets = [n for n in noms if not statuts.get(n, {}).get("ready")]
    assert pod["status"].get("phase") == "Running" and not pas_prets, message(
        en=f"The Pod is in phase {pod['status'].get('phase')!r}, containers not ready: "
        f"{pas_prets}. A busybox container with no command exits immediately: the "
        "logger must loop forever.",
        fr=f"Le Pod est en phase {pod['status'].get('phase')!r}, conteneurs non prêts : "
        f"{pas_prets}. Un conteneur busybox sans commande sort aussitôt : le "
        "logger doit tourner en boucle sans fin.",
    )


# ----------------------------------------------------------------------
# 2. Chaque conteneur a exactement son budget.
# ----------------------------------------------------------------------
def test_les_budgets_sont_ceux_demandes(host):
    conteneurs = {c["name"]: c for c in _pod(host)["spec"]["containers"]}
    for nom, attendu in ATTENDU.items():
        res = conteneurs.get(nom, {}).get("resources") or {}
        for genre in ("requests", "limits"):
            for ressource, valeur in attendu[genre].items():
                vu = (res.get(genre) or {}).get(ressource)
                assert vu == valeur, message(
                    en=f"Container {nom}: {genre}.{ressource} is {vu!r}, expected {valeur!r}. "
                    "Resources are declared container by container, under "
                    "spec.containers[].resources.",
                    fr=f"Conteneur {nom} : {genre}.{ressource} vaut {vu!r}, attendu {valeur!r}. "
                    "Les resources se déclarent conteneur par conteneur, sous "
                    "spec.containers[].resources.",
                )


# ----------------------------------------------------------------------
# 3. Labels et annotation.
# ----------------------------------------------------------------------
def test_labels_et_annotation(host):
    meta = _pod(host)["metadata"]
    labels = meta.get("labels") or {}
    for cle, valeur in LABELS.items():
        assert labels.get(cle) == valeur, message(
            en=f"Label {cle} is {labels.get(cle)!r}, expected {valeur!r}. Labels present: {labels}",
            fr=f"Le label {cle} vaut {labels.get(cle)!r}, attendu {valeur!r}. Labels présents : {labels}",
        )
    annotations = meta.get("annotations") or {}
    assert annotations.get("description", "").strip(), message(
        en="No description annotation on the Pod, or it is empty. An "
        "annotation is declared under metadata.annotations, like a label, but "
        "it only serves humans and tools, never selections.",
        fr="Aucune annotation description sur le Pod, ou elle est vide. Une "
        "annotation se déclare sous metadata.annotations, comme un label, mais "
        "elle ne sert qu'aux humains et aux outils, jamais aux sélections.",
    )


# ----------------------------------------------------------------------
# 4. La limite de mémoire est appliquée par le noyau, dans chaque conteneur.
# ----------------------------------------------------------------------
def test_la_limite_de_memoire_est_appliquee(host):
    for nom, octets in LIMITES_OCTETS.items():
        res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -c {nom} -- cat /sys/fs/cgroup/memory.max")
        assert res.rc == 0, message(
            en=f"Cannot read the cgroup in {nom}: {res.stderr.strip()[:120]}",
            fr=f"Lecture du cgroup impossible dans {nom} : {res.stderr.strip()[:120]}",
        )
        vu = res.stdout.strip()
        assert vu == str(octets), message(
            en=f"Inside container {nom}, the kernel applies memory.max = {vu!r}, expected "
            f"{octets} bytes. \"max\" means no limit applies: the "
            "declared limit is not the one running, or the Pod was not recreated "
            "after the change.",
            fr=f"Dans le conteneur {nom}, le noyau applique memory.max = {vu!r}, attendu "
            f"{octets} octets. « max » signifie qu'aucune limite ne s'applique : la "
            "limite déclarée n'est pas celle qui tourne, ou le Pod n'a pas été recréé "
            "après modification.",
        )
