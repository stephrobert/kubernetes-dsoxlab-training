"""test_functional.py : cka-daemonset-all-nodes

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Un test
vérifie un seul état.

Le compte d'un Pod par nœud se lit sur le nœud de chaque Pod, et non dans un
chiffre du statut. La tolérance se prouve par le taint du control plane,
toujours là : le retirer donnerait le même compte sans rien enseigner. Le
travail de l'agent se lit dans ses logs.

Tous échouent avant le travail : le namespace monitoring est vide. Une attente
ne s'ouvre que si le DaemonSet existe déjà.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "monitoring"
DAEMONSET = "monitor-agent"
IMAGE = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
CONTROL_PLANE = "k8s-cp.lab"
TAINT = "node-role.kubernetes.io/control-plane"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 90
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _daemonset(host) -> dict:
    ds = _json(host, f"-n {NAMESPACE} get daemonset {DAEMONSET}")
    if ds is None:
        pytest.fail(message(
            en=f"No DaemonSet {DAEMONSET} in {NAMESPACE}.",
            fr=f"Aucun DaemonSet {DAEMONSET} dans {NAMESPACE}.",
        ))
    return ds


def _pods_prets(host, ds: dict) -> list[dict]:
    selecteur = ",".join(f"{k}={v}" for k, v in ds["spec"]["selector"].get("matchLabels", {}).items())
    return [
        p for p in (_json(host, f"-n {NAMESPACE} get pods -l {selecteur}") or {}).get("items", [])
        if not p["metadata"].get("deletionTimestamp")
        and p["status"].get("phase") == "Running"
        and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
    ]


def _noeuds(host) -> list[str]:
    return sorted(n["metadata"]["name"] for n in (_json(host, "get nodes") or {}).get("items", []))


def _est_l_image(image: str | None) -> bool:
    """Même dépôt et même digest que l'image demandée ; le tag est facultatif."""
    if not image or "@" not in image:
        return False
    nom, digest = image.split("@", 1)
    nom = nom.removeprefix("docker.io/library/")
    return digest == IMAGE.split("@")[1] and nom.split(":")[0] == "busybox" \
        and (":" not in nom or nom.split(":")[1] == "1.38.0")


# ----------------------------------------------------------------------
# 1. Le DaemonSet fait tourner l'image demandée.
# ----------------------------------------------------------------------
def test_le_daemonset_porte_l_image_demandee(host):
    ds = _daemonset(host)
    images = [c.get("image") for c in ds["spec"]["template"]["spec"].get("containers") or []]
    assert any(_est_l_image(i) for i in images), message(
        en=f"The DaemonSet runs {images}. Expected the image of the instructions, referred to by digest.",
        fr=f"Le DaemonSet fait tourner {images}. Attendu l'image de l'énoncé, référencée par digest.",
    )


# ----------------------------------------------------------------------
# 2. Ses Pods portent le label demandé.
# ----------------------------------------------------------------------
def test_les_pods_portent_le_label_app_monitor(host):
    ds = _daemonset(host)
    labels = ds["spec"]["template"]["metadata"].get("labels") or {}
    assert labels.get("app") == "monitor", message(
        en=f"The Pods carry {labels}; app: monitor is required.",
        fr=f"Les Pods portent {labels} ; il faut app: monitor.",
    )


# ----------------------------------------------------------------------
# 3. Un Pod prêt sur chaque nœud.
# ----------------------------------------------------------------------
def test_un_pod_pret_sur_chaque_noeud(host):
    ds = _daemonset(host)
    noeuds = _noeuds(host)
    places = sorted(p["spec"].get("nodeName", "") for p in _pods_prets(host, ds))
    fin = time.monotonic() + ATTENTE
    while places != noeuds and time.monotonic() < fin:
        time.sleep(PAS)
        places = sorted(p["spec"].get("nodeName", "") for p in _pods_prets(host, ds))
    manquants = sorted(set(noeuds) - set(places))
    assert places == noeuds, message(
        en=f"Pods ready on {places}, cluster nodes {noeuds}: {manquants} missing. "
        + (f"{CONTROL_PLANE} carries a NoSchedule taint: without a toleration, the DaemonSet puts nothing there."
           if CONTROL_PLANE in manquants else ""),
        fr=f"Pods prêts sur {places}, nœuds du cluster {noeuds} : il manque {manquants}. "
        + (f"{CONTROL_PLANE} porte un taint NoSchedule : sans tolérance, le DaemonSet n'y met rien."
           if CONTROL_PLANE in manquants else ""),
    )


# ----------------------------------------------------------------------
# 4. Le taint est toujours là, et l'agent le tolère.
# ----------------------------------------------------------------------
def test_le_taint_est_la_et_l_agent_le_tolere(host):
    ds = _daemonset(host)
    noeud = _json(host, f"get node {CONTROL_PLANE}") or {}
    taints = [t for t in (noeud.get("spec") or {}).get("taints") or []
              if t.get("key") == TAINT and t.get("effect") == "NoSchedule"]
    assert taints, message(
        en=f"{CONTROL_PLANE} no longer has the {TAINT}:NoSchedule taint. Removing the taint does make the agent "
        "run everywhere, but it opens the control plane to every Pod: the instruction asked for a toleration in "
        "the DaemonSet.",
        fr=f"{CONTROL_PLANE} n'a plus le taint {TAINT}:NoSchedule. Retirer le taint fait tourner l'agent partout, "
        "mais ouvre le control plane à tous les Pods : la consigne demandait une tolérance dans le DaemonSet.",
    )
    tolerances = ds["spec"]["template"]["spec"].get("tolerations") or []
    bonnes = [
        t for t in tolerances
        if t.get("key") in (TAINT, None, "") and t.get("effect") in ("NoSchedule", None, "")
        and (t.get("operator") == "Exists" or t.get("value", "") == "")
    ]
    assert bonnes, message(
        en=f"The DaemonSet tolerates {tolerances}, not the {TAINT}:NoSchedule taint: key, operator and effect "
        "must match the taint of the node.",
        fr=f"Le DaemonSet tolère {tolerances}, pas le taint {TAINT}:NoSchedule : clé, opérateur et effet doivent "
        "correspondre au taint du nœud.",
    )


# ----------------------------------------------------------------------
# 5. Chaque agent fait son travail : heartbeat dans ses logs.
# ----------------------------------------------------------------------
def test_chaque_agent_ecrit_heartbeat(host):
    ds = _daemonset(host)
    pods = _pods_prets(host, ds)
    assert pods, message(
        en=f"No ready Pod of {DAEMONSET} in {NAMESPACE}.",
        fr=f"Aucun Pod prêt de {DAEMONSET} dans {NAMESPACE}.",
    )
    muets: list[str] = []
    for _ in range(6):
        muets = [f"{p['metadata']['name']} ({p['spec'].get('nodeName')})" for p in pods
                 if "heartbeat" not in host.run(f"{ADMIN} -n {NAMESPACE} logs {p['metadata']['name']} --tail=5").stdout]
        if not muets:
            return
        time.sleep(5)
    assert not muets, message(
        en=f"These agents do not write heartbeat in their logs: {muets}. The container must write it every "
        "sixty seconds, from startup, and without stopping.",
        fr=f"Ces agents n'écrivent pas heartbeat dans leurs logs : {muets}. Le conteneur doit l'écrire toutes "
        "les soixante secondes, dès le démarrage, et sans s'arrêter.",
    )
