"""test_functional.py : k8s-prioriser-et-preempter

Ces tests lisent l'état du cluster kind « multi », jamais les commandes tapées.
Un test vérifie un seul état :

1. les PriorityClass basse (1000) et haute (100000) existent, sans être la classe
   par défaut du cluster ;
2. les Pods de remplissage tournent sous la classe basse ;
3. le Pod urgent tourne, sur le worker plein (multi-worker) ;
4. un Pod de remplissage a été préempté pour lui : l'ordonnanceur l'a dit par un
   événement Preempted ;
5. le Pod urgent porte la classe haute.

Les cinq échouent sur l'état de départ : aucune classe, remplissage en priorité
0, aucun Pod urgent, aucune préemption.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kind/multi.kubeconfig"
NS = "ordonnancement"
NOEUD = "multi-worker"
CLASSES = {"basse": 1000, "haute": 100000}
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _urgent(host, attendre: bool) -> dict:
    pod = _json(host, f"-n {NS} get pod urgent")
    assert pod is not None, message(
        en=f"No Pod urgent in {NS}: the manifest ~/lab/urgent.yaml describes it.",
        fr=f"Aucun Pod urgent dans {NS} : le manifeste ~/lab/urgent.yaml le décrit.",
    )
    fin = time.monotonic() + (ATTENTE if attendre else 0)
    while pod["status"].get("phase") != "Running" and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _json(host, f"-n {NS} get pod urgent") or pod
    return pod


# ----------------------------------------------------------------------
# 1. Les deux classes existent, avec leur valeur, sans être par défaut.
# ----------------------------------------------------------------------
def test_les_deux_classes_existent(host):
    ecarts = {}
    for nom, valeur in CLASSES.items():
        pc = _json(host, f"get priorityclass {nom}")
        if pc is None:
            ecarts[nom] = message(en="missing", fr="absente")
        elif pc.get("value") != valeur or pc.get("globalDefault"):
            ecarts[nom] = f"value={pc.get('value')}, globalDefault={bool(pc.get('globalDefault'))}"
    assert not ecarts, message(
        en=f"PriorityClasses not as expected: {ecarts}. Expected basse at 1000 and haute at 100000, neither "
        "being the cluster's default class.",
        fr=f"PriorityClass non conformes : {ecarts}. Attendu basse à 1000 et haute à 100000, aucune des deux "
        "n'étant la classe par défaut du cluster.",
    )


# ----------------------------------------------------------------------
# 2. Les Pods de remplissage tournent sous la classe basse.
# ----------------------------------------------------------------------
def test_le_remplissage_tourne_sous_la_classe_basse(host):
    pods = [p for p in (_json(host, f"-n {NS} get pods -l app=remplissage") or {}).get("items", [])
            if not p["metadata"].get("deletionTimestamp")]
    en_marche = [p for p in pods if p["status"].get("phase") == "Running"]
    hors_classe = sorted(p["metadata"]["name"] for p in pods
                         if p["spec"].get("priorityClassName") != "basse" or p["spec"].get("priority") != 1000)
    assert en_marche and not hors_classe, message(
        en=f"Pods of remplissage outside the class basse: {hors_classe or 'none'}, running: {len(en_marche)}. "
        "A Pod receives its priority when it is created: the Deployment's Pods must be recreated under the class.",
        fr=f"Pods de remplissage hors de la classe basse : {hors_classe or 'aucun'}, en marche : {len(en_marche)}. "
        "Un Pod reçoit sa priorité à sa création : les Pods du Deployment doivent être recréés sous la classe.",
    )


# ----------------------------------------------------------------------
# 3. Le Pod urgent tourne, sur le worker plein.
# ----------------------------------------------------------------------
def test_le_pod_urgent_tourne(host):
    pod = _urgent(host, attendre=True)
    phase, noeud = pod["status"].get("phase"), pod["spec"].get("nodeName")
    assert phase == "Running" and noeud == NOEUD, message(
        en=f"The Pod urgent is {phase!r} on {noeud!r}; expected Running on {NOEUD}, the full worker its "
        "manifest targets.",
        fr=f"Le Pod urgent est {phase!r} sur {noeud!r} ; attendu Running sur {NOEUD}, le worker plein que vise "
        "son manifeste.",
    )


# ----------------------------------------------------------------------
# 4. Un Pod de remplissage a été préempté.
# ----------------------------------------------------------------------
def test_un_pod_de_basse_priorite_a_ete_preempte(host):
    evenements = (_json(host, f"-n {NS} get events --field-selector reason=Preempted") or {}).get("items") or []
    victimes = sorted({e["involvedObject"].get("name", "") for e in evenements
                       if e["involvedObject"].get("name", "").startswith("remplissage-")})
    assert victimes, message(
        en=f"No Pod of remplissage was preempted in {NS}: the scheduler made no room by evicting a "
        "lower-priority Pod. Room made by hand is not a preemption.",
        fr=f"Aucun Pod de remplissage n'a été préempté dans {NS} : l'ordonnanceur n'a pas fait de place en "
        "évinçant un Pod moins prioritaire. Une place faite à la main n'est pas une préemption.",
    )


# ----------------------------------------------------------------------
# 5. Le Pod urgent porte la classe haute.
# ----------------------------------------------------------------------
def test_le_pod_urgent_porte_la_classe_haute(host):
    pod = _urgent(host, attendre=False)
    classe, priorite = pod["spec"].get("priorityClassName"), pod["spec"].get("priority")
    assert classe == "haute" and priorite == CLASSES["haute"], message(
        en=f"The Pod urgent has class {classe!r} and priority {priorite!r}; expected haute, at {CLASSES['haute']}.",
        fr=f"Le Pod urgent a la classe {classe!r} et la priorité {priorite!r} ; attendu haute, à {CLASSES['haute']}.",
    )
