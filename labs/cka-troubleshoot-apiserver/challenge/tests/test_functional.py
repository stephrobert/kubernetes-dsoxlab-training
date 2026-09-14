"""test_functional.py : cka-troubleshoot-apiserver

Ces tests lisent l'état du CLUSTER et du NŒUD, jamais les commandes tapées.

Trois affirmations. La première interroge l'API ; la deuxième lit l'état du
Pod statique ; la troisième relit le manifeste sur le nœud, et c'est elle qui
prouve que la réparation en est une : un API server qui redémarre parce qu'on
a supprimé la ligne d'autorisation répond, mais il accepte tout le monde.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NOEUD = "k8s-cp.lab"
POD = f"kube-apiserver-{NOEUD}"
MANIFESTE = "/etc/kubernetes/manifests/kube-apiserver.yaml"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


# ----------------------------------------------------------------------
# 1. L'API répond.
# ----------------------------------------------------------------------
def test_l_api_repond(host):
    sante = _kubectl(host, "get --raw /healthz")
    assert sante.rc == 0 and sante.stdout.strip() == "ok", (
        "L'API server ne répond pas. kubectl est aveugle, mais le nœud ne l'est "
        "pas : le manifeste statique est dans /etc/kubernetes/manifests, crictl "
        "voit le conteneur mort et garde ses journaux, et le kubelet raconte dans "
        f"journalctl ce qu'il essaie de démarrer. Sortie : {(sante.stdout + sante.stderr).strip()[:200]}"
    )
    noeuds = _kubectl(host, "get nodes --no-headers")
    assert noeuds.rc == 0 and NOEUD in noeuds.stdout, (
        f"/healthz répond mais kubectl get nodes échoue : {noeuds.stderr.strip()[:200]}"
    )


# ----------------------------------------------------------------------
# 2. Le Pod statique tourne, sans boucle de redémarrage.
# ----------------------------------------------------------------------
def test_le_pod_statique_tourne(host):
    """Le kubelet ne marque le conteneur prêt qu'après sa sonde de readiness.

    Mesuré par scripts/valider-labs.py le 2026-09-14 : /healthz répond
    plusieurs secondes avant que le Pod miroir passe `ready`. On laisse donc
    au kubelet le temps de sa sonde, sans quoi un apprenant qui lance le check
    juste après la réparation serait recalé à tort.
    """
    pod, statut = {}, {}
    for _ in range(18):
        res = _kubectl(host, f"-n kube-system get pod {POD} -o json")
        assert res.rc == 0, (
            f"Le Pod {POD} est introuvable : soit l'API ne répond pas, soit le "
            f"manifeste a disparu du répertoire des Pods statiques. {res.stderr.strip()[:200]}"
        )
        pod = json.loads(res.stdout)
        statut = (pod["status"].get("containerStatuses") or [{}])[0]
        if pod["status"].get("phase") == "Running" and statut.get("ready"):
            return
        time.sleep(5)
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    assert False, (
        f"Après 90 s, le Pod {POD} est en phase {pod['status'].get('phase')!r}, "
        f"prêt : {statut.get('ready')}, raison d'attente : {raison}, "
        f"redémarrages : {statut.get('restartCount')}. Le conteneur sort encore "
        "au démarrage : ses journaux, par crictl logs, disent pourquoi."
    )


# ----------------------------------------------------------------------
# 3. Le manifeste est sain, et l'autorisation y est toujours.
# ----------------------------------------------------------------------
def test_le_manifeste_est_sain_et_autorise_toujours(host):
    res = host.run(f"sudo cat {MANIFESTE}")
    assert res.rc == 0, f"Impossible de lire {MANIFESTE} : {res.stderr.strip()}"
    manifeste = res.stdout
    assert "--authorization-modes=" not in manifeste, (
        "Le manifeste porte encore le flag mal orthographié "
        "--authorization-modes : l'API server ne connaît pas ce flag et sort "
        "au démarrage. Comparez-le, lettre par lettre, au flag documenté."
    )
    assert "--authorization-mode=Node,RBAC" in manifeste, (
        "Le manifeste ne déclare plus --authorization-mode=Node,RBAC. Supprimer "
        "la ligne fait bien redémarrer l'API server, mais sans mode "
        "d'autorisation il accepte toute requête authentifiée : ce n'est pas "
        "une réparation, c'est une porte ouverte. Corrigez le flag, ne le retirez pas."
    )
