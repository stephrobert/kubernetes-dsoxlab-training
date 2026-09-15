"""test_functional.py : cka-troubleshoot-kubelet

Ces tests lisent l'état du CLUSTER et du NŒUD, jamais les commandes tapées.

Trois affirmations. La première lit l'état du nœud depuis l'API ; la
deuxième interroge systemd et relit la configuration SUR le worker, et c'est
elle qui distingue une réparation d'une amputation : un kubelet qui démarre
parce qu'on a vidé clusterDNS tourne, mais ses Pods ne résolvent plus rien.
La troisième regarde l'application, qui n'a nulle part où aller sans ce nœud.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host

CONTROL_PLANE = "k8s-cp.lab"
WORKER = "k8s-w1.lab"
NAMESPACE = "production"
DEPLOYMENT = "web-app"
CONFIG = "/var/lib/kubelet/config.yaml"
DNS_LEGITIME = "10.96.0.10"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def cp():
    return lab_host(CONTROL_PLANE)


@pytest.fixture(scope="module")
def worker():
    return lab_host(WORKER)


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


# ----------------------------------------------------------------------
# 1. Le nœud est Ready.
# ----------------------------------------------------------------------
def test_le_noeud_est_ready(cp):
    """Le control plane met jusqu'à une minute à revoir un nœud : on l'attend."""
    statut = ""
    for _ in range(18):
        res = _kubectl(cp, f"get node {WORKER} -o json")
        assert res.rc == 0, f"Le nœud {WORKER} est introuvable : {res.stderr.strip()[:200]}"
        conditions = {c["type"]: c for c in json.loads(res.stdout)["status"].get("conditions", [])}
        statut = conditions.get("Ready", {}).get("status", "Unknown")
        if statut == "True":
            return
        time.sleep(5)
    assert statut == "True", (
        f"Le nœud {WORKER} est toujours NotReady (Ready = {statut}) après 90 s. "
        f"Son kubelet ne tient pas : sur le nœud, journalctl -u kubelet dit ce "
        "qu'il reproche à sa configuration."
    )


# ----------------------------------------------------------------------
# 2. Le kubelet tourne, avec une configuration saine.
# ----------------------------------------------------------------------
def test_le_kubelet_tourne_avec_une_configuration_saine(worker):
    kubelet = worker.service("kubelet")
    assert kubelet.is_running, (
        f"Le service kubelet n'est pas actif sur {WORKER}. S'il s'arrête aussitôt "
        "lancé, c'est qu'il refuse sa configuration : le journal nomme le champ."
    )
    res = worker.run(f"sudo cat {CONFIG}")
    assert res.rc == 0, f"Impossible de lire {CONFIG} : {res.stderr.strip()}"
    config = res.stdout
    assert "999.999.999.999" not in config, (
        f"{CONFIG} porte encore 999.999.999.999 dans clusterDNS. Réindenter la "
        "ligne fait démarrer le kubelet, mais 999 n'est pas un octet : ce n'est "
        "pas une adresse, et un résolveur qui n'existe pas n'a rien à faire dans "
        "la liste que le kubelet donne aux Pods. La ligne ajoutée doit partir."
    )
    assert DNS_LEGITIME in config, (
        f"{CONFIG} ne mentionne plus {DNS_LEGITIME}, l'adresse du Service "
        "kube-dns. Le kubelet démarre, mais les Pods de ce nœud ne résoudront "
        "plus aucun nom : il fallait retirer la ligne ajoutée, pas le champ."
    )


# ----------------------------------------------------------------------
# 3. L'application est revenue, sur ce nœud.
# ----------------------------------------------------------------------
def test_l_application_est_revenue_sur_le_noeud(cp):
    disponibles, voulus = 0, 0
    for _ in range(18):
        res = _kubectl(cp, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json")
        assert res.rc == 0, f"Le Deployment {DEPLOYMENT} est introuvable : {res.stderr.strip()[:200]}"
        d = json.loads(res.stdout)
        voulus = d["spec"].get("replicas", 0)
        disponibles = d["status"].get("availableReplicas", 0)
        if voulus == 3 and disponibles == 3:
            break
        time.sleep(5)
    assert voulus == 3, f"Le Deployment demande {voulus} replica(s) au lieu de 3 : il ne fallait pas y toucher."
    assert disponibles == 3, (
        f"{disponibles} replica(s) disponible(s) sur 3 après 90 s. L'application "
        f"est réservée à {WORKER} : tant que ce nœud ne peut pas l'accueillir, "
        "elle reste dégradée."
    )
    pods = _kubectl(cp, f"-n {NAMESPACE} get pods -l app={DEPLOYMENT} -o json")
    ailleurs = [
        p["metadata"]["name"] for p in json.loads(pods.stdout)["items"]
        if p["spec"].get("nodeName") != WORKER
    ]
    assert not ailleurs, (
        f"Des Pods de {DEPLOYMENT} tournent ailleurs que sur {WORKER} : {ailleurs}. "
        "Le nodeSelector a été retiré : déplacer l'application n'est pas réparer le nœud."
    )
