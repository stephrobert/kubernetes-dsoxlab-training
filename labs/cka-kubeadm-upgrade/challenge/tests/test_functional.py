"""test_functional.py : cka-kubeadm-upgrade

Deux affirmations qui lisent l'état réel du cluster, jamais les commandes
tapées.

Le dernier test exerce LES DEUX CÔTÉS. « L'application a ses deux exemplaires »
est déjà vrai AVANT le travail : isolée, cette assertion ferait un test vert
qui ne mesure rien. Accolée aux versions, elle prend tout son sens, car elle
distingue une montée conduite d'une montée qui a emporté le service.

Le contrôle des nœuds ordonnançables est le troisième larron, et il attrape
l'oubli le plus coûteux de cette procédure : un nœud vidé pour être monté reste
inordonnançable tant qu'on ne l'a pas rendu, et le cluster tourne alors avec un
nœud en moins sans que rien ne le signale.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "supervision"
DEPLOYMENT = "sonde"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
VERSION_CIBLE = "v1.37.0"
VERSION_DEPART = "v1.36.4"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _noeuds(host) -> list[dict]:
    rc, sortie, diagnostic = _kubectl(host, "get nodes -o json")
    assert rc == 0 and sortie, (
        f"Le cluster ne répond pas. Une montée de version interrompue laisse "
        "un plan de contrôle muet : `sudo systemctl status kubelet` et "
        f"`sudo crictl ps -a` sur le nœud disent où elle s'est arrêtée. {diagnostic}"
    )
    return json.loads(sortie)["items"]


# ----------------------------------------------------------------------
# 1. Le plan de contrôle porte la version visée.
# ----------------------------------------------------------------------
def test_le_plan_de_controle_est_monte(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable. Monter le plan de contrôle
    sans monter les nœuds laisse un cluster à moitié fait, qui fonctionne et
    qui est pourtant faux."""
    rc, sortie, diagnostic = _kubectl(
        host, "version -o json --request-timeout=30s"
    )
    assert rc == 0 and sortie, f"Impossible de lire la version. {diagnostic}"
    serveur = json.loads(sortie).get("serverVersion", {}).get("gitVersion", "")
    assert serveur.startswith(VERSION_CIBLE), (
        f"L'API server annonce « {serveur or 'rien'} » et non {VERSION_CIBLE}. "
        f"Le cluster est parti de {VERSION_DEPART} : c'est `kubeadm upgrade "
        "apply` sur le plan de contrôle qui applique une version au cluster, et "
        "il faut que kubeadm lui-même soit déjà à cette version pour savoir ce "
        "qu'elle attend."
    )


# ----------------------------------------------------------------------
# 2. LE test : tous les nœuds sont montés, ordonnançables, et l'application
#    sert toujours.
# ----------------------------------------------------------------------
def test_tous_les_noeuds_sont_montes_et_le_service_tient(host):
    """La preuve, prise sur chaque nœud et sur l'application.

    Mesuré le 2026-09-17 : `kubeadm upgrade apply` ne monte PAS le kubelet. Le
    paquet se remplace à la main, nœud par nœud, et le service se redémarre.
    Un nœud oublié continue d'annoncer l'ancienne version sans que rien ne
    casse, ce qui est précisément le piège de cette tâche.
    """
    noeuds = _noeuds(host)
    assert noeuds, "Le cluster ne déclare aucun nœud."

    en_retard = {
        n["metadata"]["name"]: n["status"]["nodeInfo"]["kubeletVersion"]
        for n in noeuds
        if not n["status"]["nodeInfo"]["kubeletVersion"].startswith(VERSION_CIBLE)
    }
    assert not en_retard, (
        f"Ces nœuds annoncent encore une autre version : {en_retard}. "
        "`kubeadm upgrade apply` ne monte pas le kubelet : le paquet se "
        "remplace nœud par nœud et le service se redémarre. Sur un worker, la "
        "commande n'est d'ailleurs pas la même que sur le plan de contrôle : "
        "seul celui-ci applique une version au cluster."
    )

    vides = [
        n["metadata"]["name"] for n in noeuds if n["spec"].get("unschedulable")
    ]
    assert not vides, (
        f"Ces nœuds sont restés inordonnançables : {vides}. Vider un nœud "
        "avant de le monter est la bonne façon de faire, mais il faut le "
        "rendre ensuite : le cluster tourne sinon avec un nœud en moins, et "
        "rien ne le signale. `kubectl get nodes` affiche alors "
        "SchedulingDisabled."
    )

    pas_prets = [
        n["metadata"]["name"] for n in noeuds
        if not any(
            c["type"] == "Ready" and c["status"] == "True"
            for c in n["status"].get("conditions", [])
        )
    ]
    assert not pas_prets, (
        f"Ces nœuds ne sont pas Ready : {pas_prets}. Un kubelet monté qui ne "
        "redémarre pas, ou qui redémarre avec une configuration qu'il ne "
        "comprend pas, laisse le nœud dans cet état : `sudo journalctl -u "
        "kubelet -n 50` le dit."
    )

    rc, pretes, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} get deployment {DEPLOYMENT} "
        "-o jsonpath='{.status.readyReplicas}'",
    )
    assert rc == 0 and pretes == "2", (
        f"L'application {DEPLOYMENT} n'a que « {pretes or 'aucun'} » "
        "exemplaire(s) prêt(s) sur deux. Une montée de version ne doit pas "
        "emporter ce qui tourne : vider un nœud déplace ses Pods, elle ne les "
        f"supprime pas. {diagnostic}"
    )
