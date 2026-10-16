"""test_functional.py : ckad-troubleshoot-missing-configmap

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. La première lit le ConfigMap ; la deuxième l'état du
Pod ; la troisième interroge l'application depuis le nœud, et c'est elle qui
prouve que le fichier monté est bien celui qu'elle attendait : un ConfigMap
créé vide débloquerait le Pod et ferait servir une page vide.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "broken-app"
CONFIGMAP = "app-settings"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, message(
        en=f"No Pod {POD} in {NAMESPACE}: it was not to be deleted, only unblocked.",
        fr=f"Aucun Pod {POD} dans {NAMESPACE} : il ne fallait pas le supprimer, seulement le débloquer.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Le ConfigMap existe, avec la clé et le contenu attendus.
# ----------------------------------------------------------------------
def test_le_configmap_porte_la_configuration(host):
    res = _kubectl(host, f"-n {NAMESPACE} get configmap {CONFIGMAP} -o json")
    assert res.rc == 0, message(
        en=f"No ConfigMap {CONFIGMAP} in {NAMESPACE}. That is what the Pod is waiting for: "
        "its events name it, at the bottom of kubectl describe pod.",
        fr=f"Aucun ConfigMap {CONFIGMAP} dans {NAMESPACE}. C'est ce que le Pod attend : "
        "ses events le nomment, en bas de kubectl describe pod.",
    )
    data = json.loads(res.stdout).get("data") or {}
    assert "settings.conf" in data, message(
        en=f"{CONFIGMAP} exists but has no settings.conf key: the Pod mounts the ConfigMap "
        f"as a directory, and reads that file. Keys: {sorted(data) or 'none'}",
        fr=f"{CONFIGMAP} existe mais n'a pas de clé settings.conf : le Pod monte le ConfigMap "
        f"comme un répertoire, et lit ce fichier. Clés : {sorted(data) or 'aucune'}",
    )
    assert "mode=production" in data["settings.conf"], message(
        en=f"settings.conf does not contain 'mode=production': {data['settings.conf'][:100]!r}",
        fr=f"settings.conf ne contient pas 'mode=production' : {data['settings.conf'][:100]!r}",
    )


# ----------------------------------------------------------------------
# 2. Le Pod s'est débloqué, sans avoir été recréé.
# ----------------------------------------------------------------------
def test_le_pod_est_running(host):
    pod = {}
    for _ in range(18):
        pod = _pod(host)
        if pod["status"].get("phase") == "Running":
            break
        time.sleep(5)
    statut = (pod["status"].get("containerStatuses") or [{}])[0]
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    assert pod["status"].get("phase") == "Running" and statut.get("ready"), message(
        en=f"Pod {POD} is in phase {pod['status'].get('phase')!r}, reason {raison}. "
        "A volume referencing a missing ConfigMap keeps the Pod in "
        "ContainerCreating; the kubelet retries by itself as soon as it exists.",
        fr=f"Le Pod {POD} est en phase {pod['status'].get('phase')!r}, raison {raison}. "
        "Un volume qui référence un ConfigMap absent bloque le Pod en "
        "ContainerCreating ; le kubelet réessaie tout seul dès qu'il existe.",
    )


# ----------------------------------------------------------------------
# 3. La preuve : l'application sert la configuration qu'elle a lue.
# ----------------------------------------------------------------------
def test_l_application_sert_sa_configuration(host):
    ip = _pod(host)["status"].get("podIP")
    assert ip, message(
        en="The Pod has no IP address.",
        fr="Le Pod n'a pas d'adresse IP.",
    )
    res = host.run(f"curl -sS -m 5 http://{ip}/")
    assert res.rc == 0, message(
        en=f"Nothing answers on http://{ip}/ from the node: {res.stderr.strip()[:150]}",
        fr=f"Rien ne répond sur http://{ip}/ depuis le nœud : {res.stderr.strip()[:150]}",
    )
    assert "mode=production" in res.stdout, message(
        en=f"The application answers, but not with its configuration: {res.stdout.strip()[:120]!r}. "
        "It copies /config/settings.conf into its page at startup: the mounted "
        "file is not the expected one.",
        fr=f"L'application répond, mais pas avec sa configuration : {res.stdout.strip()[:120]!r}. "
        "Elle recopie /config/settings.conf dans sa page au démarrage : le fichier "
        "monté n'est pas celui attendu.",
    )
