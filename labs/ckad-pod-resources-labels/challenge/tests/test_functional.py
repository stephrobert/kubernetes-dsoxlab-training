"""test_functional.py : ckad-pod-resources-labels

Ces tests lisent la définition du Pod multi-app, son état, puis la limite de
mémoire que le noyau applique, lue dans le cgroup de chaque conteneur. Un test
vérifie un seul état demandé par l'énoncé.

Tous échouent avant le travail : le Pod n'existe pas. L'attente du Pod Running
ne s'ouvre que s'il existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "multi-app"
IMAGES = {
    "web": "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb",
    "logger": "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4",
}
BUDGETS = {
    "web": {"requests": {"cpu": "100m", "memory": "64Mi"}, "limits": {"cpu": "200m", "memory": "128Mi"}},
    "logger": {"requests": {"cpu": "50m", "memory": "32Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
}
LIMITES_OCTETS = {"web": 128 * 1024 * 1024, "logger": 64 * 1024 * 1024}
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 90
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} get pod {POD} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _absent() -> str:
    return message(en=f"No Pod {POD} in {NS}.", fr=f"Aucun Pod {POD} dans {NS}.")


def _verifier_budget(host, nom: str) -> None:
    pod = _pod(host)
    assert pod is not None, _absent()
    res = {c["name"]: c.get("resources") or {} for c in pod["spec"]["containers"]}.get(nom, {})
    vu = {g: {r: (res.get(g) or {}).get(r) for r in BUDGETS[nom][g]} for g in ("requests", "limits")}
    assert vu == BUDGETS[nom], message(
        en=f"Container {nom} declares {vu}, expected {BUDGETS[nom]}. Budgets are declared container by "
        "container, never at the level of the Pod.",
        fr=f"Le conteneur {nom} déclare {vu}, attendu {BUDGETS[nom]}. Les budgets se déclarent conteneur par "
        "conteneur, jamais au niveau du Pod.",
    )


# ----------------------------------------------------------------------
# 1. multi-app tourne avec ses deux conteneurs.
# ----------------------------------------------------------------------
def test_multi_app_tourne_avec_ses_deux_conteneurs(host):
    pod = _pod(host)
    assert pod is not None, _absent()
    fin = time.monotonic() + ATTENTE
    while pod["status"].get("phase") != "Running" and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _pod(host) or pod
    images = {c["name"]: c.get("image") for c in pod["spec"]["containers"]}
    prets = {s["name"]: s.get("ready") for s in pod["status"].get("containerStatuses") or []}
    assert images == IMAGES and all(prets.get(n) for n in IMAGES), message(
        en=f"{POD} carries the containers {images}, ready: {prets}. Expected exactly web and logger, on the "
        "images of the requirements, both running. A busybox container with nothing to do exits at once.",
        fr=f"{POD} porte les conteneurs {images}, prêts : {prets}. Attendu exactement web et logger, sur les "
        "images du cahier des charges, tous deux en marche. Un conteneur busybox qui n'a rien à faire sort "
        "aussitôt.",
    )


# ----------------------------------------------------------------------
# 2. et 3. Chaque conteneur a son budget.
# ----------------------------------------------------------------------
def test_web_a_son_budget(host):
    _verifier_budget(host, "web")


def test_logger_a_son_budget(host):
    _verifier_budget(host, "logger")


# ----------------------------------------------------------------------
# 4. Le noyau applique la limite de mémoire dans chaque conteneur.
# ----------------------------------------------------------------------
def test_le_noyau_applique_la_limite_de_memoire_de_chaque_conteneur(host):
    assert _pod(host) is not None, _absent()
    lus = {}
    for nom in LIMITES_OCTETS:
        res = host.run(f"{ADMIN} -n {NS} exec {POD} -c {nom} -- cat /sys/fs/cgroup/memory.max")
        lus[nom] = res.stdout.strip() if res.rc == 0 else "illisible"
    attendus = {n: str(o) for n, o in LIMITES_OCTETS.items()}
    assert lus == attendus, message(
        en=f"Inside the containers, the kernel applies the memory limits {lus}, expected {attendus} bytes. "
        "\"max\" means that no limit applies: the declared limit is not the one running.",
        fr=f"Dans les conteneurs, le noyau applique les limites de mémoire {lus}, attendu {attendus} octets. "
        "« max » signifie qu'aucune limite ne s'applique : la limite déclarée n'est pas celle qui tourne.",
    )
