"""test_functional.py : cks-runtime-sandbox-gvisor

Deux affirmations qui lisent l'état du cluster et l'intérieur des conteneurs,
jamais les commandes tapées.

Le dernier test compare le noyau que voient DEUX Pods : celui du bac à sable et
un Pod ordinaire posé par le setup. C'est une preuve qui ne se truque pas, et
qui ne tient à aucune chaîne de caractères choisie par nous : un Pod ordinaire
lit le noyau de la machine, un Pod confiné lit celui que le bac à sable lui
présente, et les deux ne peuvent pas être identiques.

Sans le Pod témoin, on ne saurait pas distinguer « le bac à sable isole » de
« tous les Pods de ce nœud voient ce noyau-là ».
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "bac-a-sable"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CONFINE = "confine"
TEMOIN = "ordinaire"
RUNTIME_CLASS = "gvisor"
HANDLER = "runsc"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _noyau(host, pod: str) -> str:
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} exec {pod} --request-timeout=30s -- cat /proc/version"
    )
    assert rc == 0 and sortie, (
        f"Impossible de lire le noyau depuis le Pod {pod}. Sortie : {diagnostic}"
    )
    return sortie


# ----------------------------------------------------------------------
# 1. La RuntimeClass existe et désigne le bon runtime.
# ----------------------------------------------------------------------
def test_la_runtimeclass_designe_le_runtime_du_noeud(host):
    """Ce test ne prouve rien à lui seul : une RuntimeClass peut exister et
    désigner un runtime que containerd ne connaît pas, auquel cas les Pods
    restent bloqués. Il est là pour que l'échec soit diagnosticable."""
    rc, sortie, diagnostic = _kubectl(host, f"get runtimeclass {RUNTIME_CLASS} -o json")
    assert rc == 0 and sortie, (
        f"Aucune RuntimeClass nommée {RUNTIME_CLASS}. C'est un objet de CLUSTER, "
        "sans namespace : il fait le pont entre un nom que les Pods emploient et "
        f"un runtime que containerd connaît. Sortie : {diagnostic}"
    )
    handler = json.loads(sortie).get("handler")
    assert handler == HANDLER, (
        f"La RuntimeClass désigne le handler « {handler} ». containerd connaît "
        f"ce runtime sous le nom « {HANDLER} », et le nom doit correspondre "
        "exactement : sinon le Pod reste en attente, sans message clair."
    )


# ----------------------------------------------------------------------
# 2. LE test : le Pod confiné ne voit pas le noyau de la machine.
# ----------------------------------------------------------------------
def test_le_pod_confine_ne_voit_pas_le_noyau_de_l_hote(host):
    """La preuve, prise dans les deux conteneurs et comparée.

    Elle ne dépend d'aucune chaîne que nous aurions choisie : on ne cherche pas
    le mot « gvisor », on constate que le Pod confiné et le Pod ordinaire ne
    lisent pas le même noyau, et que celui du Pod ordinaire est bien celui de
    la machine.

    Mesuré le 2026-09-16 : le Pod confiné lit « Linux version 4.19.0-gvisor »,
    le nœud tourne sous « 6.8.0-139-generic ».
    """
    rc, phase, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} get pod {CONFINE} -o jsonpath='{{.status.phase}}'"
    )
    assert rc == 0 and phase, (
        f"Aucun Pod {CONFINE} dans {NAMESPACE}. {diagnostic}"
    )
    assert phase == "Running", (
        f"Le Pod {CONFINE} est en {phase}. Un runtimeClassName qui désigne un "
        "runtime inconnu de containerd laisse le Pod en attente : "
        "`kubectl describe pod` le dit dans ses events."
    )

    rc, declare, _ = _kubectl(
        host, f"-n {NAMESPACE} get pod {CONFINE} -o jsonpath='{{.spec.runtimeClassName}}'"
    )
    assert rc == 0 and declare == RUNTIME_CLASS, (
        f"Le Pod {CONFINE} déclare runtimeClassName « {declare or 'rien'} ». "
        f"Il doit employer la classe {RUNTIME_CLASS} pour être placé dans le "
        "bac à sable."
    )

    noyau_confine = _noyau(host, CONFINE)
    noyau_temoin = _noyau(host, TEMOIN)
    res = host.run("uname -r")
    noyau_machine = res.stdout.strip()

    assert noyau_machine and noyau_machine in noyau_temoin, (
        f"Le Pod témoin ne lit pas le noyau de la machine ({noyau_machine}), "
        f"mais « {noyau_temoin} ». Le setup l'avait pourtant lancé avec le "
        "runtime par défaut : sans ce point de comparaison, la mesure qui suit "
        "ne veut rien dire."
    )
    assert noyau_machine not in noyau_confine, (
        f"Le Pod {CONFINE} lit le noyau de la machine : « {noyau_confine} ». Il "
        "n'est donc pas dans le bac à sable, il partage le noyau de l'hôte "
        "comme n'importe quel conteneur. Vérifiez que son runtimeClassName est "
        "bien pris en compte, et que le Pod a été RECRÉÉ après : ce champ ne se "
        "modifie pas sur un Pod existant."
    )
    assert noyau_confine != noyau_temoin, (
        "Les deux Pods lisent exactement le même noyau : aucun des deux n'est "
        "isolé."
    )
