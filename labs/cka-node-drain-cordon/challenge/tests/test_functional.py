"""test_functional.py : cka-node-drain-cordon

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le budget et son état calculé : un
selector qui ne matche rien donne un PDB qui ne protège rien. La deuxième
prouve que l'évacuation a eu lieu : chaque Pod de web est né après l'heure
notée par le setup, aucun ne tourne plus sur le worker, le Pod orphelin est
parti et le DaemonSet du CNI est resté. La troisième veut le worker de retour
dans le scheduling, et comme un nœud jamais cordonné l'est aussi, elle exige
en plus que l'évacuation ait eu lieu. La quatrième lit la trace.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

WORKER = "k8s-w1.lab"
NAMESPACE = "lab"
DEPLOYMENT = "web"
PDB = "web-pdb"
ORPHELIN = "outil-diag"
CONFIGMAP = "drain-evidence"
ANNOTATION = "lab.dsoxlab/pose-le"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str) -> dict:
    res = _kubectl(host, args + " -o json")
    assert res.rc == 0, f"kubectl {args} échoue : {res.stderr.strip()[:200]}"
    return json.loads(res.stdout)


def _pods_web(host) -> list[dict]:
    return [
        p for p in _json(host, f"-n {NAMESPACE} get pods -l app={DEPLOYMENT}")["items"]
        if not p["metadata"].get("deletionTimestamp")
    ]


def _heure_de_pose(host) -> str:
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}")
    heure = (d["metadata"].get("annotations") or {}).get(ANNOTATION)
    assert heure, f"Le Deployment {DEPLOYMENT} n'a plus l'annotation {ANNOTATION} posée par le setup."
    return heure


def _evacuation_a_eu_lieu(host) -> None:
    """Chaque Pod de web est né après la pose, et aucun n'est sur le worker."""
    pose = _heure_de_pose(host)
    pods = _pods_web(host)
    assert len(pods) == 4, f"{len(pods)} Pod(s) de {DEPLOYMENT} au lieu de 4 : il ne fallait pas toucher aux replicas."
    anciens = [p["metadata"]["name"] for p in pods if p["metadata"]["creationTimestamp"] <= pose]
    assert not anciens, (
        f"Ces Pods de {DEPLOYMENT} datent d'avant le début du lab : {anciens}. Un drain évince "
        "chaque Pod du nœud et le contrôleur le recrée ailleurs : les Pods d'origine ne "
        "survivent pas à l'opération. Ceux-ci n'ont jamais été évincés."
    )
    sur_worker = [p["metadata"]["name"] for p in pods if p["spec"].get("nodeName") == WORKER]
    assert not sur_worker, (
        f"Des Pods de {DEPLOYMENT} tournent encore sur {WORKER} : {sur_worker}. Le nœud n'a pas "
        "été évacué, ou l'a été avant d'être retiré du scheduling et le scheduler y a "
        "remis des Pods."
    )


# ----------------------------------------------------------------------
# 1. Le budget existe, et il protège vraiment l'application.
# ----------------------------------------------------------------------
def test_le_budget_protege_l_application(host):
    res = _kubectl(host, f"-n {NAMESPACE} get pdb {PDB} -o json")
    assert res.rc == 0, (
        f"Aucun PodDisruptionBudget {PDB} dans {NAMESPACE}. Sans budget, un drain évince "
        "tous les Pods du nœud d'un coup, et le service tombe le temps qu'ils reviennent."
    )
    pdb = json.loads(res.stdout)
    assert pdb["spec"].get("minAvailable") == 2, (
        f"minAvailable vaut {pdb['spec'].get('minAvailable')!r} au lieu de 2 "
        f"(maxUnavailable : {pdb['spec'].get('maxUnavailable')!r}). La consigne demande au "
        "moins deux Pods disponibles à tout moment."
    )
    attendus = 0
    for _ in range(12):
        attendus = (pdb.get("status") or {}).get("expectedPods", 0)
        if attendus == 4:
            break
        time.sleep(5)
        pdb = _json(host, f"-n {NAMESPACE} get pdb {PDB}")
    assert attendus == 4, (
        f"Le budget compte {attendus} Pod(s) attendu(s) au lieu de 4 : son selector ne "
        f"matche pas les Pods de {DEPLOYMENT}. Un budget qui ne vise rien ne protège rien."
    )


# ----------------------------------------------------------------------
# 2. L'évacuation a eu lieu, et elle a respecté ce qu'il fallait.
# ----------------------------------------------------------------------
def test_le_worker_a_ete_evacue(host):
    _evacuation_a_eu_lieu(host)
    res = _kubectl(host, f"-n {NAMESPACE} get pod {ORPHELIN} -o json")
    assert res.rc != 0 or json.loads(res.stdout)["metadata"].get("deletionTimestamp"), (
        f"Le Pod {ORPHELIN} est toujours sur le worker. Il n'a aucun contrôleur et le drain "
        "le refuse par défaut : la consigne dit qu'il peut disparaître, et l'option existe."
    )
    calico = [
        p for p in _json(host, "-n kube-system get pods -l k8s-app=calico-node")["items"]
        if p["spec"].get("nodeName") == WORKER and not p["metadata"].get("deletionTimestamp")
    ]
    assert calico, (
        f"Aucun Pod calico-node sur {WORKER} : le DaemonSet du réseau a été supprimé. Un "
        "drain doit ignorer les DaemonSets, pas les faire disparaître."
    )


# ----------------------------------------------------------------------
# 3. Le worker est revenu dans le scheduling, après avoir été vidé.
# ----------------------------------------------------------------------
def test_le_worker_est_remis_en_service(host):
    _evacuation_a_eu_lieu(host)
    noeud = _json(host, f"get node {WORKER}")
    assert not noeud["spec"].get("unschedulable", False), (
        f"{WORKER} est toujours hors du scheduling (SchedulingDisabled). La maintenance "
        "est finie : il faut le remettre en service, sinon tout tourne sur un seul nœud."
    )
    conditions = {c["type"]: c["status"] for c in noeud["status"].get("conditions", [])}
    assert conditions.get("Ready") == "True", f"{WORKER} n'est pas Ready (Ready = {conditions.get('Ready')})."


# ----------------------------------------------------------------------
# 4. La trace de l'opération.
# ----------------------------------------------------------------------
def test_la_trace_est_ecrite(host):
    res = _kubectl(host, f"-n {NAMESPACE} get configmap {CONFIGMAP} -o json")
    assert res.rc == 0, f"Aucun ConfigMap {CONFIGMAP} dans {NAMESPACE}."
    data = json.loads(res.stdout).get("data") or {}
    assert data.get("drained-node") == WORKER, (
        f"drained-node vaut {data.get('drained-node')!r}, attendu {WORKER!r}."
    )
    assert data.get("status") == "completed", f"status vaut {data.get('status')!r}, attendu 'completed'."
