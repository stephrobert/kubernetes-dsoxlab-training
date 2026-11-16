"""test_functional.py : cka-control-plane-haute-disponibilite

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Le setup
laisse trois nœuds prêts pour kubeadm (ha-cp1, ha-cp2, ha-cp3) et un
répartiteur HAProxy sur ha-lb.lab, sans cluster. L'apprenant initialise le
premier plan de contrôle derrière le répartiteur, joint les deux autres en
plans de contrôle, et pose un CNI.

Rien n'est vrai avant le travail : il n'existe ni admin.conf, ni nœud, ni
etcd. Le dernier test PROUVE la haute disponibilité au lieu de la croire : il
arrête ha-cp2 (kubelet et conteneurs), écrit dans le cluster par le
répartiteur, puis relance ha-cp2 et attend qu'il revienne.
"""

from __future__ import annotations

import json
import time
import uuid

import pytest

from conftest import lab_host, lab_host_ip, lab_target_host, message

PLANS = ("ha-cp1.lab", "ha-cp2.lab", "ha-cp3.lab")
REPARTITEUR = "ha-lb.lab"
VICTIME = "ha-cp2.lab"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ETCDCTL = (
    "--endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt "
    "--cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key"
)


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("ha-cp1.lab"))


def _json(host, commande: str) -> dict:
    res = host.run(f"{KUBECTL} {commande} -o json")
    assert res.rc == 0, message(
        en=f"`kubectl {commande}` failed on ha-cp1: {res.stderr.strip()}. Is the cluster initialised, and "
        "/etc/kubernetes/admin.conf present?",
        fr=f"`kubectl {commande}` a échoué sur ha-cp1 : {res.stderr.strip()}. Le cluster est-il initialisé, et "
        "/etc/kubernetes/admin.conf présent ?",
    )
    return json.loads(res.stdout)


def _noeuds_prets(host) -> dict[str, tuple[bool, str, bool]]:
    """Par nœud : prêt, version du kubelet, rôle control-plane."""
    etat = {}
    for n in _json(host, "get nodes")["items"]:
        conditions = {c["type"]: c["status"] for c in n["status"].get("conditions", [])}
        etat[n["metadata"]["name"]] = (
            conditions.get("Ready") == "True",
            n["status"]["nodeInfo"]["kubeletVersion"],
            "node-role.kubernetes.io/control-plane" in n["metadata"].get("labels", {}),
        )
    return etat


def _court(nom: str) -> str:
    return nom.split(".")[0]


# ----------------------------------------------------------------------
# 1. Le point d'accès du cluster est le répartiteur.
# ----------------------------------------------------------------------
def test_le_point_d_acces_est_le_repartiteur(host):
    cm = _json(host, "-n kube-system get configmap kubeadm-config")
    config = cm["data"]["ClusterConfiguration"]
    ligne = next((x for x in config.splitlines() if x.strip().startswith("controlPlaneEndpoint:")), "")
    point = ligne.split(":", 1)[1].strip().strip("\"'") if ligne else ""
    acceptes = {f"{REPARTITEUR}:6443", f"{_court(REPARTITEUR)}:6443", f"{lab_host_ip(REPARTITEUR)}:6443"}
    assert point in acceptes, message(
        en=f"The controlPlaneEndpoint of the cluster is {point or 'absent'!r}: it must be the load balancer, "
        f"{REPARTITEUR}:6443. It cannot be changed after kubeadm init: reset with `kubeadm reset -f` and start "
        "again.",
        fr=f"Le controlPlaneEndpoint du cluster vaut {point or 'absent'!r} : il doit être le répartiteur, "
        f"{REPARTITEUR}:6443. Il ne se modifie plus après kubeadm init : repartez de `kubeadm reset -f`.",
    )


# ----------------------------------------------------------------------
# 2. Trois plans de contrôle Ready, en 1.37.
# ----------------------------------------------------------------------
def test_trois_plans_de_controle_sont_ready(host):
    fin = time.time() + 120
    while True:
        etat = _noeuds_prets(host)
        manquants = [p for p in PLANS if not any(n in (p, _court(p)) and e[0] and e[2] for n, e in etat.items())]
        if not manquants or time.time() > fin:
            break
        time.sleep(5)
    assert not manquants, message(
        en=f"These nodes are not Ready control planes: {manquants} (cluster seen from ha-cp1: {etat}). A node "
        "joined without --control-plane is a worker; a NotReady node often lacks its CNI.",
        fr=f"Ces nœuds ne sont pas des plans de contrôle Ready : {manquants} (cluster vu de ha-cp1 : {etat}). Un "
        "nœud joint sans --control-plane est un worker ; un nœud NotReady manque souvent de son CNI.",
    )
    versions = {n: e[1] for n, e in etat.items()}
    assert all(v.startswith("v1.37.") for v in versions.values()), message(
        en=f"Every kubelet must report 1.37: {versions}.",
        fr=f"Chaque kubelet doit annoncer 1.37 : {versions}.",
    )


# ----------------------------------------------------------------------
# 3. etcd compte trois membres votants, tous sains.
# ----------------------------------------------------------------------
def _etcd(host, sous_commande: str):
    """etcdctl joué dans le Pod etcd de ha-cp1 : etcdctl n'est pas installé sur un nœud kubeadm."""
    pods = _json(host, "-n kube-system get pods -l component=etcd")["items"]
    pod = next(
        (p["metadata"]["name"] for p in pods if p["spec"].get("nodeName", "").startswith("ha-cp1")),
        "etcd-ha-cp1.lab",
    )
    return host.run(f"{KUBECTL} -n kube-system exec {pod} -- etcdctl {ETCDCTL} {sous_commande}")


def test_etcd_compte_trois_membres_votants_sains(host):
    liste = _etcd(host, "member list -w json")
    assert liste.rc == 0, message(
        en=f"etcdctl member list fails in the etcd Pod of ha-cp1: {liste.stderr.strip()}",
        fr=f"etcdctl member list échoue dans le Pod etcd de ha-cp1 : {liste.stderr.strip()}",
    )
    membres = json.loads(liste.stdout).get("members", [])
    votants = [m.get("name") for m in membres if not m.get("isLearner")]
    assert len(votants) == 3 and len(membres) == 3, message(
        en=f"etcd has {len(membres)} members, {len(votants)} of them voting ({votants}): three voting members "
        "are expected, one per control plane (stacked etcd).",
        fr=f"etcd compte {len(membres)} membres, dont {len(votants)} votants ({votants}) : trois membres votants "
        "sont attendus, un par plan de contrôle (etcd empilé).",
    )
    sante = _etcd(host, "endpoint health --cluster")
    assert sante.rc == 0, message(
        en=f"A member of etcd does not answer: {sante.stdout.strip()} {sante.stderr.strip()}",
        fr=f"Un membre d'etcd ne répond pas : {sante.stdout.strip()} {sante.stderr.strip()}",
    )


# ----------------------------------------------------------------------
# 4. L'API survit à la perte d'un plan de contrôle.
# ----------------------------------------------------------------------
def _arreter(victime) -> None:
    victime.run(
        "sudo systemctl stop kubelet && sudo crictl ps -q | xargs -r sudo crictl stop -t 5 > /dev/null"
    )


def _relancer(victime) -> None:
    victime.run("sudo systemctl start kubelet")


def test_l_api_repond_par_le_repartiteur_apres_la_perte_d_un_plan_de_controle(host):
    serveur = _json(host, "config view --minify")["clusters"][0]["cluster"]["server"]
    assert REPARTITEUR in serveur or _court(REPARTITEUR) in serveur or lab_host_ip(REPARTITEUR) in serveur, message(
        en=f"admin.conf talks to {serveur}, not to the load balancer: kubectl would lose the API with that node.",
        fr=f"admin.conf parle à {serveur}, pas au répartiteur : kubectl perdrait l'API avec ce nœud.",
    )
    victime = lab_host(VICTIME)
    _arreter(victime)
    try:
        time.sleep(15)
        fin = time.time() + 90
        reussites, dernier = 0, ""
        while reussites < 5 and time.time() < fin:
            nom = f"ha-preuve-{uuid.uuid4().hex[:6]}"
            res = host.run(f"{KUBECTL} -n default create configmap {nom} --request-timeout=10s")
            if res.rc == 0:
                reussites += 1
                host.run(f"{KUBECTL} -n default delete configmap {nom} --request-timeout=10s")
            else:
                reussites, dernier = 0, res.stderr.strip()
                time.sleep(3)
        assert reussites >= 5, message(
            en=f"With {VICTIME} down, the cluster no longer accepts writes through the load balancer: {dernier}. "
            "Three voting etcd members keep the quorum with two; HAProxy removes a backend after its failed "
            "checks.",
            fr=f"Avec {VICTIME} arrêté, le cluster n'accepte plus d'écriture par le répartiteur : {dernier}. Trois "
            "membres etcd votants gardent le quorum à deux ; HAProxy retire un serveur après ses contrôles en "
            "échec.",
        )
    finally:
        _relancer(victime)
    fin = time.time() + 180
    while time.time() < fin:
        if _etcd(host, "endpoint health --cluster").rc == 0:
            break
        time.sleep(10)
    assert _etcd(host, "endpoint health --cluster").rc == 0, message(
        en=f"{VICTIME} was restarted but its etcd member did not come back within 3 minutes.",
        fr=f"{VICTIME} a été relancé mais son membre etcd n'est pas revenu en 3 minutes.",
    )
