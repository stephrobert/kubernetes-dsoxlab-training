"""test_functional.py : k8s-annoncer-un-service-en-bgp

Cinq tests, un par état demandé. Le cluster est lu par son API, mais les
preuves viennent du ROUTEUR, hors du cluster : sessions établies, routes
apprises, et une requête HTTP partie de son espace réseau vers l'adresse de
LoadBalancer, par la route qu'il a reçue en BGP.

Le routeur FRR tourne sur l'hôte témoin (k8s-cp.lab), dans un conteneur lancé
par ctr (espace de noms containerd « dsoxlab ») et un espace de noms réseau à
lui (dsoxlab-frr).
"""

from __future__ import annotations

import ipaddress
import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "bgp-demo"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
POOL = ipaddress.ip_network("172.30.0.0/28")
ROUTEUR = "sudo ctr -n dsoxlab task exec --exec-id test-{n} routeur-frr vtysh -c '{commande}'"
BUDGET_S = 90
PAS_S = 5
_compteur = [0]


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("net-cp.lab"))


@pytest.fixture(scope="module")
def temoin():
    return lab_host("k8s-cp.lab")


def _kubectl(host, args: str):
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str) -> dict:
    rc, sortie, _ = _kubectl(host, f"{args} -o json")
    if rc != 0 or not sortie:
        return {}
    return json.loads(sortie)


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _routeur(temoin, commande: str) -> dict:
    """Une commande vtysh en JSON sur le routeur, ou {} si elle échoue."""
    _compteur[0] += 1
    res = temoin.run(ROUTEUR.format(n=_compteur[0], commande=commande))
    debut = res.stdout.find("{")
    if res.rc != 0 or debut < 0:
        return {}
    try:
        return json.loads(res.stdout[debut:])
    except json.JSONDecodeError:
        return {}


def _pairs(temoin) -> dict:
    return _routeur(temoin, "show bgp summary json").get("ipv4Unicast", {}).get("peers", {})


def _routes(temoin) -> dict:
    return _routeur(temoin, "show bgp ipv4 unicast json").get("routes", {})


def _ip_lb(host) -> str:
    svc = _json(host, f"-n {NAMESPACE} get service web")
    entrees = svc.get("status", {}).get("loadBalancer", {}).get("ingress") or []
    return entrees[0].get("ip", "") if entrees else ""


# ----------------------------------------------------------------------
# 1. Le plan de contrôle BGP de Cilium est activé.
# ----------------------------------------------------------------------
def test_le_plan_de_controle_bgp_est_active(host):
    _, valeur, _ = _kubectl(host, "-n kube-system get configmap cilium-config -o jsonpath='{.data.enable-bgp-control-plane}'")
    assert valeur == "true", message(
        en=f"enable-bgp-control-plane is {valeur or 'absent'} in cilium-config: set the Helm value "
        "bgpControlPlane.enabled=true.",
        fr=f"enable-bgp-control-plane vaut {valeur or 'absent'} dans cilium-config : posez la valeur Helm "
        "bgpControlPlane.enabled=true.",
    )
    ds = _attendre(
        lambda: _json(host, "-n kube-system get daemonset cilium"),
        lambda d: d.get("status", {}).get("numberReady") == d.get("status", {}).get("desiredNumberScheduled")
        and d.get("status", {}).get("updatedNumberScheduled") == d.get("status", {}).get("desiredNumberScheduled"),
    )
    statut = ds.get("status", {})
    assert statut.get("numberReady") == statut.get("desiredNumberScheduled"), message(
        en=f"The Cilium agents are not all ready: {statut.get('numberReady')}/{statut.get('desiredNumberScheduled')}.",
        fr=f"Les agents Cilium ne sont pas tous prêts : {statut.get('numberReady')}/"
        f"{statut.get('desiredNumberScheduled')}.",
    )


# ----------------------------------------------------------------------
# 2. Le routeur a une session établie avec chacun des trois nœuds.
# ----------------------------------------------------------------------
def test_les_trois_sessions_sont_etablies(host, temoin):
    pairs = _attendre(lambda: _pairs(temoin), lambda p: len(p) == 3 and all(
        v.get("state") == "Established" for v in p.values()))
    assert pairs, message(
        en="The router does not answer (vtysh on k8s-cp.lab): run dsoxlab reset.",
        fr="Le routeur ne répond pas (vtysh sur k8s-cp.lab) : lancez dsoxlab reset.",
    )
    etats = {ip: v.get("state", "?") for ip, v in pairs.items()}
    assert all(e == "Established" for e in etats.values()), message(
        en=f"Sessions seen by the router: {etats}. The router is AS 65000 at 10.10.50.200 and expects each node "
        "in AS 65001. Active or Connect means the node does not answer, or answers with another AS: check "
        "localASN, peerASN, peerAddress, and the label that the nodeSelector of the CiliumBGPClusterConfig "
        "requires on each node.",
        fr=f"Sessions vues par le routeur : {etats}. Le routeur est l'AS 65000 à 10.10.50.200 et attend chaque "
        "nœud en AS 65001. Active ou Connect veut dire que le nœud ne répond pas, ou répond avec un autre AS : "
        "vérifiez localASN, peerASN, peerAddress, et l'étiquette que le nodeSelector du CiliumBGPClusterConfig "
        "exige sur chaque nœud.",
    )


# ----------------------------------------------------------------------
# 3. Le réseau des Pods de chaque nœud est annoncé.
# ----------------------------------------------------------------------
def test_le_reseau_des_pods_est_annonce(host, temoin):
    attendus = sorted({
        c for n in _json(host, "get ciliumnodes").get("items", [])
        for c in (n.get("spec", {}).get("ipam", {}).get("podCIDRs") or [])
    })
    routes = _attendre(lambda: _routes(temoin), lambda r: all(c in r for c in attendus))
    manquants = [c for c in attendus if c not in routes]
    assert attendus and not manquants, message(
        en=f"The router has not learnt the Pod networks {manquants or attendus} (learnt: {sorted(routes)}). "
        "A CiliumBGPAdvertisement of type PodCIDR, selected by the CiliumBGPPeerConfig of the peer, announces "
        "them.",
        fr=f"Le routeur n'a pas appris les réseaux de Pods {manquants or attendus} (appris : {sorted(routes)}). "
        "Une CiliumBGPAdvertisement de type PodCIDR, sélectionnée par le CiliumBGPPeerConfig du pair, les "
        "annonce.",
    )


# ----------------------------------------------------------------------
# 4. Le Service web a une adresse du pool, et le routeur l'a apprise.
# ----------------------------------------------------------------------
def test_l_adresse_de_loadbalancer_est_annoncee(host, temoin):
    ip = _attendre(lambda: _ip_lb(host), bool)
    assert ip and ipaddress.ip_address(ip) in POOL, message(
        en=f"The Service web of {NAMESPACE} has the address {ip or '<pending>'}, expected one from {POOL}. A "
        "CiliumLoadBalancerIPPool gives addresses to Services of type LoadBalancer.",
        fr=f"Le Service web de {NAMESPACE} a l'adresse {ip or '<pending>'}, attendu une adresse de {POOL}. Un "
        "CiliumLoadBalancerIPPool donne leurs adresses aux Services de type LoadBalancer.",
    )
    routes = _attendre(lambda: _routes(temoin), lambda r: f"{ip}/32" in r)
    assert f"{ip}/32" in routes, message(
        en=f"The router has not learnt {ip}/32 (learnt: {sorted(routes)}). The advertisement of type Service "
        "with addresses LoadBalancerIP selects the Service by its labels: the Service web carries annonce-bgp=oui.",
        fr=f"Le routeur n'a pas appris {ip}/32 (appris : {sorted(routes)}). L'annonce de type Service avec "
        "addresses LoadBalancerIP sélectionne le Service par ses étiquettes : le Service web porte "
        "annonce-bgp=oui.",
    )


# ----------------------------------------------------------------------
# 5. Depuis le routeur, l'application répond à l'adresse annoncée.
# ----------------------------------------------------------------------
def test_l_application_repond_depuis_le_routeur(host, temoin):
    ip = _ip_lb(host)
    assert ip, message(
        en="The Service web has no address: the previous test says why.",
        fr="Le Service web n'a pas d'adresse : le test précédent dit pourquoi.",
    )

    def demander() -> str:
        res = temoin.run(f"sudo ip netns exec dsoxlab-frr curl -s --max-time 5 http://{ip}/")
        return res.stdout

    page = _attendre(demander, lambda p: "<title>Welcome to nginx!</title>" in p, budget=45)
    assert "<title>Welcome to nginx!</title>" in page, message(
        en=f"From the router's network, http://{ip}/ does not return the nginx page ({page[:80]!r}). The route "
        "is learnt but the traffic does not come back: is the Service still served by its Pods?",
        fr=f"Depuis le réseau du routeur, http://{ip}/ ne rend pas la page de nginx ({page[:80]!r}). La route "
        "est apprise mais le trafic ne revient pas : le Service est-il toujours servi par ses Pods ?",
    )
