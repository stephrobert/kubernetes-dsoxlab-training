"""test_functional.py : cka-daemonset-all-nodes

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le DaemonSet, son image et son label.
La deuxième compte un Pod prêt par nœud, en lisant le nœud de chaque Pod et
non un chiffre du statut. La troisième prouve la tolérance : le taint du
control plane est toujours là, et un Pod y tourne quand même ; retirer le
taint aurait donné le même compte sans rien enseigner. La quatrième lit les
logs de chaque agent, là où le travail se voit.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "monitoring"
DAEMONSET = "monitor-agent"
IMAGE = "busybox:1.37"
CONTROL_PLANE = "k8s-cp.lab"
TAINT = "node-role.kubernetes.io/control-plane"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str) -> dict:
    res = _kubectl(host, args + " -o json")
    assert res.rc == 0, message(
        en=f"kubectl {args} failed: {res.stderr.strip()[:200]}",
        fr=f"kubectl {args} échoue : {res.stderr.strip()[:200]}",
    )
    return json.loads(res.stdout)


def _daemonset(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get daemonset {DAEMONSET} -o json")
    assert res.rc == 0, message(
        en=f"No DaemonSet {DAEMONSET} in {NAMESPACE}.",
        fr=f"Aucun DaemonSet {DAEMONSET} dans {NAMESPACE}.",
    )
    return json.loads(res.stdout)


def _pods_prets(host) -> list[dict]:
    return [
        p for p in _json(host, f"-n {NAMESPACE} get pods -l app=monitor")["items"]
        if not p["metadata"].get("deletionTimestamp")
        and p["status"].get("phase") == "Running"
        and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
    ]


def _noeuds(host) -> list[str]:
    return sorted(n["metadata"]["name"] for n in _json(host, "get nodes")["items"])


# ----------------------------------------------------------------------
# 1. Le DaemonSet existe, avec l'image et le label demandés.
# ----------------------------------------------------------------------
def test_le_daemonset_est_declare(host):
    ds = _daemonset(host)
    labels = ds["spec"]["template"]["metadata"].get("labels") or {}
    assert labels.get("app") == "monitor", message(
        en=f"The Pods carry {labels}; app: monitor is required.",
        fr=f"Les Pods portent {labels} ; il faut app: monitor.",
    )
    conteneurs = ds["spec"]["template"]["spec"].get("containers") or []
    images = [c.get("image") for c in conteneurs]
    assert IMAGE in images, message(
        en=f"The DaemonSet uses {images}, expected {IMAGE}.",
        fr=f"Le DaemonSet utilise {images}, attendu {IMAGE}.",
    )


# ----------------------------------------------------------------------
# 2. Un Pod prêt sur chaque nœud.
# ----------------------------------------------------------------------
def test_un_pod_pret_sur_chaque_noeud(host):
    _daemonset(host)
    noeuds = _noeuds(host)
    places: list[str] = []
    for _ in range(18):
        places = sorted(p["spec"].get("nodeName", "") for p in _pods_prets(host))
        if places == noeuds:
            return
        time.sleep(5)
    manquants = sorted(set(noeuds) - set(places))
    assert places == noeuds, message(
        en=f"Pods ready on {places}, cluster nodes {noeuds}: {manquants} missing. "
        + (f"{CONTROL_PLANE} carries a NoSchedule taint: without a toleration, the DaemonSet puts nothing there." if CONTROL_PLANE in manquants else ""),
        fr=f"Pods prêts sur {places}, nœuds du cluster {noeuds} : il manque {manquants}. "
        + (f"{CONTROL_PLANE} porte un taint NoSchedule : sans tolérance, le DaemonSet n'y met rien." if CONTROL_PLANE in manquants else ""),
    )


# ----------------------------------------------------------------------
# 3. La preuve : le taint est toujours là, et l'agent tourne dessus.
# ----------------------------------------------------------------------
def test_le_taint_est_la_et_l_agent_le_tolere(host):
    noeud = _json(host, f"get node {CONTROL_PLANE}")
    taints = [t for t in noeud["spec"].get("taints") or [] if t.get("key") == TAINT and t.get("effect") == "NoSchedule"]
    assert taints, message(
        en=f"{CONTROL_PLANE} no longer has the {TAINT}:NoSchedule taint. Removing the taint does "
        "make the agent run everywhere, but it opens the control plane to every Pod: the "
        "instruction asked for a toleration in the DaemonSet, not an unprotected control plane.",
        fr=f"{CONTROL_PLANE} n'a plus le taint {TAINT}:NoSchedule. Retirer le taint fait tourner "
        "l'agent partout, mais ouvre le control plane à tous les Pods : la consigne demandait "
        "une tolérance dans le DaemonSet, pas un control plane sans protection.",
    )
    tolerances = _daemonset(host)["spec"]["template"]["spec"].get("tolerations") or []
    bonnes = [
        t for t in tolerances
        if t.get("key") in (TAINT, None, "") and t.get("effect") in ("NoSchedule", None, "")
        and (t.get("operator") == "Exists" or t.get("value", "") == "")
    ]
    assert bonnes, message(
        en=f"The DaemonSet tolerates {tolerances}, not the {TAINT}:NoSchedule taint. The key, "
        "the operator and the effect are copied from kubectl describe node.",
        fr=f"Le DaemonSet tolère {tolerances}, pas le taint {TAINT}:NoSchedule. La clé, "
        "l'opérateur et l'effet se recopient depuis kubectl describe node.",
    )
    sur_cp = [p["metadata"]["name"] for p in _pods_prets(host) if p["spec"].get("nodeName") == CONTROL_PLANE]
    assert sur_cp, message(
        en=f"No Pod of {DAEMONSET} ready on {CONTROL_PLANE}, although the taint is tolerated.",
        fr=f"Aucun Pod de {DAEMONSET} prêt sur {CONTROL_PLANE}, alors que le taint est toléré.",
    )


# ----------------------------------------------------------------------
# 4. Chaque agent fait son travail : heartbeat dans ses logs.
# ----------------------------------------------------------------------
def test_chaque_agent_ecrit_heartbeat(host):
    pods = _pods_prets(host)
    assert pods, message(
        en=f"No ready Pod of {DAEMONSET} in {NAMESPACE}.",
        fr=f"Aucun Pod prêt de {DAEMONSET} dans {NAMESPACE}.",
    )
    muets: list[str] = []
    for _ in range(6):
        muets = []
        for p in pods:
            res = _kubectl(host, f"-n {NAMESPACE} logs {p['metadata']['name']} --tail=5")
            if "heartbeat" not in res.stdout:
                muets.append(f"{p['metadata']['name']} sur {p['spec'].get('nodeName')}")
        if not muets:
            return
        time.sleep(5)
    assert not muets, message(
        en=f"These agents do not write heartbeat in their logs: {muets}. The container must "
        "write it every sixty seconds, from startup, and without stopping.",
        fr=f"Ces agents n'écrivent pas heartbeat dans leurs logs : {muets}. Le conteneur doit "
        "l'écrire toutes les soixante secondes, dès le démarrage, et sans s'arrêter.",
    )
