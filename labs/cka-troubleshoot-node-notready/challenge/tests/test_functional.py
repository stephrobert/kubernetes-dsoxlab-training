"""test_functional.py : cka-troubleshoot-node-notready

Ces tests lisent l'état du CLUSTER et du NŒUD, jamais les commandes tapées.

Trois affirmations. La première lit l'état du nœud depuis l'API ; la
deuxième interroge systemd SUR le worker, et c'est elle qui distingue une
réparation durable d'une réparation d'une heure : un kubelet démarré mais
resté désactivé ne reviendra pas au prochain redémarrage. La troisième
regarde l'application, qui n'a nulle part où aller sans ce nœud.
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
        "Son agent ne donne pas de nouvelles au control plane : allez voir sur le "
        f"nœud, avec ssh {WORKER}, ce que systemd dit du kubelet."
    )


# ----------------------------------------------------------------------
# 2. Le kubelet tourne, et il survivra à un redémarrage.
# ----------------------------------------------------------------------
def test_le_kubelet_tourne_et_survivra_au_redemarrage(worker):
    kubelet = worker.service("kubelet")
    assert kubelet.is_running, (
        f"Le service kubelet n'est pas actif sur {WORKER}. Tant qu'il ne tourne "
        "pas, le nœud reste NotReady : systemctl status kubelet, puis démarrez-le."
    )
    assert kubelet.is_enabled, (
        f"Le kubelet tourne sur {WORKER}, mais il est désactivé : au prochain "
        "redémarrage de la machine, il ne reviendra pas, et la panne non plus "
        "ne sera pas réparée. Un service se démarre ET s'active."
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
        "elle reste dégradée. Un nœud Ready et un kubelet actif y suffisent."
    )
    pods = _kubectl(cp, f"-n {NAMESPACE} get pods -l app={DEPLOYMENT} -o json")
    ailleurs = [
        p["metadata"]["name"] for p in json.loads(pods.stdout)["items"]
        if p["spec"].get("nodeName") != WORKER
    ]
    assert not ailleurs, (
        f"Des Pods de {DEPLOYMENT} tournent ailleurs que sur {WORKER} : {ailleurs}. "
        "Le nodeSelector a été retiré : l'application est réservée à ce nœud, "
        "et la déplacer n'est pas réparer le nœud."
    )
