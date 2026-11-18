"""test_functional.py : k8s-faire-sortir-le-trafic-par-une-passerelle

Quatre tests, un par état demandé. Ils lisent la configuration de Cilium et
les politiques, puis font sortir deux Pods vers un témoin HORS du cluster
(k8s-cp.lab), qui répond par l'adresse source qu'il voit. Jamais un fichier
de l'apprenant.

Pourquoi le test 4 lit les deux Pods à la fois : le Pod non visé sort par son
propre nœud avant tout travail. Pris seul, ce constat serait vrai avant le
travail. Ce qui prouve une politique ciblée, c'est le CONTRASTE : le Pod visé
sort par net-w2.lab pendant que l'autre, sur le même nœud, sort toujours par
net-w1.lab.
"""

from __future__ import annotations

import ipaddress
import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "egress-demo"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
PASSERELLE = "net-w2.lab"
NOEUD_DES_PODS = "net-w1.lab"
BUDGET_S = 60
PAS_S = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("net-cp.lab"))


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


def _config(host, cle: str) -> str:
    _, valeur, _ = _kubectl(host, f"-n kube-system get configmap cilium-config -o jsonpath='{{.data.{cle}}}'")
    return valeur


def _ip_du_noeud(host, noeud: str) -> str:
    for a in _json(host, f"get node {noeud}").get("status", {}).get("addresses", []):
        if a.get("type") == "InternalIP":
            return a.get("address", "")
    return ""


def _temoin(host) -> str:
    _, url, _ = _kubectl(host, f"-n {NAMESPACE} get configmap temoin -o jsonpath='{{.data.url}}'")
    return url


def _labels_correspondent(selecteur: dict, labels: dict) -> bool:
    attendus = selecteur.get("matchLabels") or {}
    return bool(attendus) and all(labels.get(k) == v for k, v in attendus.items())


def _politiques(host) -> list:
    return _json(host, "get ciliumegressgatewaypolicies.cilium.io").get("items", [])


def _vise_le_pod(politique: dict) -> bool:
    """La politique sélectionne-t-elle sortie-controlee de egress-demo, et pas autre ?"""
    labels_vise = {"app": "sortie-controlee", "io.kubernetes.pod.namespace": NAMESPACE}
    labels_autre = {"app": "autre", "io.kubernetes.pod.namespace": NAMESPACE}
    selecteurs = politique.get("spec", {}).get("selectors") or []
    vise = any(_labels_correspondent(s.get("podSelector") or {}, labels_vise) for s in selecteurs)
    autre = any(_labels_correspondent(s.get("podSelector") or {}, labels_autre) for s in selecteurs)
    return vise and not autre


# ----------------------------------------------------------------------
# 1. La passerelle d'egress est activée, avec le masquage BPF qu'elle exige.
# ----------------------------------------------------------------------
def test_la_passerelle_d_egress_est_activee(host):
    """egressGateway.enabled=true sans bpf.masquerade=true : l'agent refuse de
    démarrer (level=fatal), et le DaemonSet reste à moitié déployé."""
    # Cilium 1.20.5 écrit enable-egress-gateway. La clé
    # enable-ipv4-egress-gateway, lue par la première version de ce test, est
    # absente de cilium-config (validation du 2026-11-17).
    egress, masque = _config(host, "enable-egress-gateway"), _config(host, "enable-bpf-masquerade")
    assert egress == "true" and masque == "true", message(
        en=f"In cilium-config, enable-egress-gateway={egress or 'absent'} and enable-bpf-masquerade="
        f"{masque or 'absent'}: both must be true. The egress gateway requires BPF masquerading; without it, "
        "the agent stops at startup with level=fatal.",
        fr=f"Dans cilium-config, enable-egress-gateway={egress or 'absent'} et enable-bpf-masquerade="
        f"{masque or 'absent'} : les deux doivent valoir true. La passerelle d'egress exige le masquage BPF ; "
        "sans lui, l'agent s'arrête au démarrage en level=fatal.",
    )
    ds = _attendre(
        lambda: _json(host, "-n kube-system get daemonset cilium"),
        lambda d: d.get("status", {}).get("numberReady") == d.get("status", {}).get("desiredNumberScheduled")
        and d.get("status", {}).get("updatedNumberScheduled") == d.get("status", {}).get("desiredNumberScheduled"),
    )
    statut = ds.get("status", {})
    assert statut.get("numberReady") == statut.get("desiredNumberScheduled"), message(
        en=f"The Cilium agents are not all ready: {statut.get('numberReady')}/{statut.get('desiredNumberScheduled')}. "
        "kubectl -n kube-system logs of a failing agent says why.",
        fr=f"Les agents Cilium ne sont pas tous prêts : {statut.get('numberReady')}/"
        f"{statut.get('desiredNumberScheduled')}. kubectl -n kube-system logs d'un agent en échec dit pourquoi.",
    )


# ----------------------------------------------------------------------
# 2. Une politique vise sortie-controlee, et lui seul.
# ----------------------------------------------------------------------
def test_une_politique_vise_le_pod_sortie_controlee(host):
    politiques = _politiques(host)
    assert politiques, message(
        en="No CiliumEgressGatewayPolicy in the cluster.",
        fr="Aucune CiliumEgressGatewayPolicy dans le cluster.",
    )
    assert any(_vise_le_pod(p) for p in politiques), message(
        en=f"No policy selects the Pod sortie-controlee of {NAMESPACE} without also selecting autre "
        f"(read: {[p['metadata']['name'] for p in politiques]}). A podSelector names the Pod's label app and its "
        "namespace with the label io.kubernetes.pod.namespace.",
        fr=f"Aucune politique ne sélectionne le Pod sortie-controlee de {NAMESPACE} sans sélectionner aussi autre "
        f"(lu : {[p['metadata']['name'] for p in politiques]}). Un podSelector nomme l'étiquette app du Pod et "
        "son namespace par l'étiquette io.kubernetes.pod.namespace.",
    )


# ----------------------------------------------------------------------
# 3. La politique couvre le témoin et désigne net-w2.lab comme passerelle.
# ----------------------------------------------------------------------
def test_la_politique_couvre_le_temoin_et_designe_net_w2(host):
    url = _temoin(host)
    ip_temoin = url.split("//", 1)[-1].split(":", 1)[0] if url else ""
    labels = {
        n["metadata"]["name"]: n["metadata"].get("labels", {})
        for n in _json(host, "get nodes").get("items", [])
    }
    retenues = [p for p in _politiques(host) if _vise_le_pod(p)]
    for p in retenues:
        spec = p.get("spec", {})
        cidrs = spec.get("destinationCIDRs") or []
        couvre = bool(ip_temoin) and any(
            ipaddress.ip_address(ip_temoin) in ipaddress.ip_network(c, strict=False) for c in cidrs
        )
        selecteur = (spec.get("egressGateway") or {}).get("nodeSelector") or {}
        noeuds = sorted(n for n, lb in labels.items() if _labels_correspondent(selecteur, lb))
        if couvre and noeuds == [PASSERELLE]:
            return
    detail = "; ".join(
        f"{p['metadata']['name']}: destinationCIDRs={p.get('spec', {}).get('destinationCIDRs')}, "
        f"nodeSelector={(p.get('spec', {}).get('egressGateway') or {}).get('nodeSelector')}"
        for p in retenues
    ) or "aucune politique ne vise le Pod"
    pytest.fail(message(
        en=f"The policy must cover the witness {ip_temoin or '(ConfigMap temoin unreadable)'} in destinationCIDRs, "
        f"and its egressGateway.nodeSelector must match {PASSERELLE} and no other node. Read: {detail}. Label "
        "the gateway node, then select it by that label.",
        fr=f"La politique doit couvrir le témoin {ip_temoin or '(ConfigMap temoin illisible)'} dans "
        f"destinationCIDRs, et son egressGateway.nodeSelector doit désigner {PASSERELLE} et aucun autre nœud. "
        f"Lu : {detail}. Étiquetez le nœud passerelle, puis sélectionnez-le par cette étiquette.",
    ))


# ----------------------------------------------------------------------
# 4. Le témoin voit le Pod visé sortir par net-w2, et l'autre par net-w1.
# ----------------------------------------------------------------------
def test_le_pod_vise_sort_par_la_passerelle_et_l_autre_non(host):
    url = _temoin(host)
    assert url, message(
        en=f"ConfigMap temoin unreadable in {NAMESPACE}: run dsoxlab reset.",
        fr=f"ConfigMap temoin illisible dans {NAMESPACE} : lancez dsoxlab reset.",
    )
    ip_passerelle, ip_noeud = _ip_du_noeud(host, PASSERELLE), _ip_du_noeud(host, NOEUD_DES_PODS)

    def source(pod: str) -> str:
        rc, sortie, diag = _kubectl(host, f"-n {NAMESPACE} exec {pod} -- wget -qO- -T 5 {url}")
        return sortie if rc == 0 else f"échec ({diag.splitlines()[-1] if diag else rc})"

    vue = _attendre(lambda: source("sortie-controlee"), lambda s: s == ip_passerelle)
    assert vue == ip_passerelle, message(
        en=f"The witness sees sortie-controlee coming from {vue}, expected the gateway {PASSERELLE} "
        f"({ip_passerelle}). A timeout means the policy points to a node that is not a gateway any more; the "
        "address of net-w1 means the policy does not apply. cilium-dbg bpf egress list, in an agent, shows "
        "what the datapath learnt.",
        fr=f"Le témoin voit sortie-controlee arriver de {vue}, attendu la passerelle {PASSERELLE} "
        f"({ip_passerelle}). Un délai dépassé veut dire que la politique désigne un nœud qui n'est plus "
        "passerelle ; l'adresse de net-w1, que la politique ne s'applique pas. cilium-dbg bpf egress list, dans "
        "un agent, montre ce que le datapath a appris.",
    )
    autre = source("autre")
    assert autre == ip_noeud, message(
        en=f"The witness sees autre coming from {autre}, expected its own node {NOEUD_DES_PODS} ({ip_noeud}): "
        "the policy must not catch it.",
        fr=f"Le témoin voit autre arriver de {autre}, attendu son propre nœud {NOEUD_DES_PODS} ({ip_noeud}) : "
        "la politique ne doit pas l'attraper.",
    )
