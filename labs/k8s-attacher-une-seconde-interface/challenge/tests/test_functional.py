"""test_functional.py : k8s-attacher-une-seconde-interface

Cinq tests, un par état demandé, dans l'ordre de l'énoncé. Ils lisent l'API du
cluster et font passer une vraie requête par le second réseau, jamais un
fichier de l'apprenant.

Pourquoi le digest de l'image de Multus : le manifeste du tag v4.3.2 pointe
l'image mobile snapshot-thick (relevé le 2026-11-17). Un Multus « qui marche »
peut donc ne pas être la v4.3.2. Seul l'imageID des conteneurs en marche dit
ce qui tourne.

Pourquoi deux requêtes au test 5 : la même page, lue par l'adresse du second
réseau ET par l'adresse du Pod sur le premier, prouve que c'est bien le même
serveur derrière les deux, et que la seconde interface n'a pas cassé la
première.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "multus-demo"
NAD = "reseau-stockage"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
DIGEST = "sha256:109b885d8752fe7a7bc3b2371750bfad6789b8b8e2d0b0820b337386ba9b93c9"
ADRESSES = {"client": "192.168.100.11", "serveur": "192.168.100.12"}
NOEUDS = {"client": "net-w1.lab", "serveur": "net-w2.lab"}
BUDGET_S = 90
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


def _statut_reseaux(pod: dict) -> list:
    brut = pod.get("metadata", {}).get("annotations", {}).get("k8s.v1.cni.cncf.io/network-status", "")
    try:
        return json.loads(brut) if brut else []
    except json.JSONDecodeError:
        return []


def _pod_pret(pod: dict) -> bool:
    return any(
        c.get("type") == "Ready" and c.get("status") == "True"
        for c in pod.get("status", {}).get("conditions", []) or []
    )


# ----------------------------------------------------------------------
# 1. Cilium laisse sa place à un autre plugin CNI.
# ----------------------------------------------------------------------
def test_cilium_n_est_plus_exclusif(host):
    """En cni.exclusive=true, l'agent Cilium renomme en .cilium_bak tout autre
    fichier de /etc/cni/net.d, celui de Multus compris, sans un message."""
    rc, valeur, _ = _kubectl(host, "-n kube-system get configmap cilium-config -o jsonpath='{.data.cni-exclusive}'")
    assert rc == 0 and valeur == "false", message(
        en=f"cni-exclusive is {valeur or 'absent'} in the ConfigMap cilium-config. In exclusive mode, the "
        "Cilium agent renames any other file of /etc/cni/net.d to .cilium_bak, Multus's included. Set the Helm "
        "value cni.exclusive=false with helm upgrade --reuse-values.",
        fr=f"cni-exclusive vaut {valeur or 'absent'} dans la ConfigMap cilium-config. En mode exclusif, l'agent "
        "Cilium renomme en .cilium_bak tout autre fichier de /etc/cni/net.d, celui de Multus compris. Posez la "
        "valeur Helm cni.exclusive=false par helm upgrade --reuse-values.",
    )
    ds = _attendre(
        lambda: _json(host, "-n kube-system get daemonset cilium"),
        lambda d: d.get("status", {}).get("numberReady") == d.get("status", {}).get("desiredNumberScheduled")
        and d.get("status", {}).get("updatedNumberScheduled") == d.get("status", {}).get("desiredNumberScheduled"),
    )
    statut = ds.get("status", {})
    assert statut.get("numberReady") == statut.get("desiredNumberScheduled"), message(
        en=f"The Cilium agents are not all ready after the change: {statut.get('numberReady')}/"
        f"{statut.get('desiredNumberScheduled')}.",
        fr=f"Les agents Cilium ne sont pas tous prêts après le changement : {statut.get('numberReady')}/"
        f"{statut.get('desiredNumberScheduled')}.",
    )


# ----------------------------------------------------------------------
# 2. Multus v4.3.2 thick tourne sur chaque nœud, image épinglée.
# ----------------------------------------------------------------------
def test_multus_v4_3_2_tourne_sur_chaque_noeud(host):
    ds = _json(host, "-n kube-system get daemonset kube-multus-ds")
    assert ds, message(
        en="No DaemonSet kube-multus-ds in kube-system: Multus is not installed. /opt/multus/multus-daemonset-thick.yml "
        "is the thick manifest of v4.3.2, image pinned.",
        fr="Aucun DaemonSet kube-multus-ds dans kube-system : Multus n'est pas installé. "
        "/opt/multus/multus-daemonset-thick.yml est le manifeste thick de la v4.3.2, image épinglée.",
    )
    pods = _attendre(
        lambda: _json(host, "-n kube-system get pods -l app=multus").get("items", []),
        lambda ps: len(ps) == 3 and all(_pod_pret(p) for p in ps),
    )
    prets = [p for p in pods if _pod_pret(p)]
    assert len(prets) == 3, message(
        en=f"{len(prets)} Multus Pod(s) ready out of 3 nodes.",
        fr=f"{len(prets)} Pod(s) Multus prêt(s) sur 3 nœuds.",
    )
    images = sorted({
        cs.get("imageID", "") for p in pods for cs in p.get("status", {}).get("containerStatuses", []) or []
    })
    assert images and all(i.endswith(DIGEST) for i in images), message(
        en=f"Multus does not run the v4.3.2 image ({', '.join(images)}). The manifest of the v4.3.2 tag points to "
        "the moving image snapshot-thick: pin multus-cni:v4.3.2-thick by its digest.",
        fr=f"Multus ne fait pas tourner l'image v4.3.2 ({', '.join(images)}). Le manifeste du tag v4.3.2 pointe "
        "l'image mobile snapshot-thick : épinglez multus-cni:v4.3.2-thick par son digest.",
    )


# ----------------------------------------------------------------------
# 3. La NetworkAttachmentDefinition décrit le second réseau.
# ----------------------------------------------------------------------
def test_la_definition_du_second_reseau_existe(host):
    nad = _json(host, f"-n {NAMESPACE} get network-attachment-definitions.k8s.cni.cncf.io {NAD}")
    assert nad, message(
        en=f"No NetworkAttachmentDefinition {NAD} in {NAMESPACE}.",
        fr=f"Aucune NetworkAttachmentDefinition {NAD} dans {NAMESPACE}.",
    )
    try:
        conf = json.loads(nad.get("spec", {}).get("config", "") or "{}")
    except json.JSONDecodeError as e:
        pytest.fail(message(
            en=f"spec.config of {NAD} is not valid JSON: {e}.",
            fr=f"spec.config de {NAD} n'est pas un JSON valide : {e}.",
        ))
    attendu = {"type": "macvlan", "master": "enp1s0"}
    lu = {k: conf.get(k) for k in attendu}
    ipam = (conf.get("ipam") or {}).get("type")
    assert lu == attendu and ipam == "static", message(
        en=f"{NAD} must describe a macvlan network on enp1s0 with static addressing: read {lu}, ipam {ipam}.",
        fr=f"{NAD} doit décrire un réseau macvlan sur enp1s0, à adressage static : lu {lu}, ipam {ipam}.",
    )


# ----------------------------------------------------------------------
# 4. Deux Pods, sur deux nœuds, ont chacun deux interfaces.
# ----------------------------------------------------------------------
def test_deux_pods_ont_deux_interfaces(host):
    for nom, ip in ADRESSES.items():
        pod = _attendre(
            lambda nom=nom: _json(host, f"-n {NAMESPACE} get pod {nom}"),
            _pod_pret,
        )
        assert pod, message(
            en=f"No Pod {nom} in {NAMESPACE}.",
            fr=f"Aucun Pod {nom} dans {NAMESPACE}.",
        )
        noeud = pod.get("spec", {}).get("nodeName", "")
        assert noeud == NOEUDS[nom], message(
            en=f"The Pod {nom} runs on {noeud or 'no node'}, expected {NOEUDS[nom]}: the exchange must cross "
            "from one node to the other.",
            fr=f"Le Pod {nom} tourne sur {noeud or 'aucun nœud'}, attendu {NOEUDS[nom]} : l'échange doit "
            "passer d'un nœud à l'autre.",
        )
        assert _pod_pret(pod), message(
            en=f"The Pod {nom} is not Ready. kubectl describe pod {nom} -n {NAMESPACE} shows the CNI error, "
            "if the sandbox could not be created.",
            fr=f"Le Pod {nom} n'est pas Ready. kubectl describe pod {nom} -n {NAMESPACE} montre l'erreur CNI, "
            "si le bac à sable n'a pas pu être créé.",
        )
        reseaux = _statut_reseaux(pod)
        primaire = [r for r in reseaux if r.get("default")]
        second = [r for r in reseaux if r.get("name") == f"{NAMESPACE}/{NAD}"]
        assert primaire and second, message(
            en=f"The Pod {nom} does not report two networks in its annotation k8s.v1.cni.cncf.io/network-status "
            f"(read: {[r.get('name') for r in reseaux] or 'nothing'}). Without that annotation, Multus did not "
            "handle the Pod: is 00-multus.conf the first file of /etc/cni/net.d on its node, or was it renamed "
            "to .cilium_bak?",
            fr=f"Le Pod {nom} ne déclare pas deux réseaux dans son annotation k8s.v1.cni.cncf.io/network-status "
            f"(lu : {[r.get('name') for r in reseaux] or 'rien'}). Sans cette annotation, Multus n'a pas traité "
            "le Pod : 00-multus.conf est-il le premier fichier de /etc/cni/net.d sur son nœud, ou a-t-il été "
            "renommé en .cilium_bak ?",
        )
        assert ip in (second[0].get("ips") or []), message(
            en=f"The second interface of {nom} has {second[0].get('ips')}, expected {ip}.",
            fr=f"La seconde interface de {nom} porte {second[0].get('ips')}, attendu {ip}.",
        )


# ----------------------------------------------------------------------
# 5. Le client joint le serveur par le second réseau, et le premier marche encore.
# ----------------------------------------------------------------------
def test_le_client_joint_le_serveur_par_le_second_reseau(host):
    serveur = _json(host, f"-n {NAMESPACE} get pod serveur")
    ip_primaire = serveur.get("status", {}).get("podIP", "")
    assert ip_primaire, message(
        en="The Pod serveur has no address on the cluster network: the previous test says why.",
        fr="Le Pod serveur n'a pas d'adresse sur le réseau du cluster : le test précédent dit pourquoi.",
    )

    def lire(ip: str) -> tuple[int, str]:
        rc, sortie, diag = _kubectl(host, f"-n {NAMESPACE} exec client -- wget -qO- -T 5 http://{ip}:8080/")
        return rc, sortie or diag

    rc2, par_second = _attendre(lambda: lire(ADRESSES["serveur"]), lambda v: v[0] == 0 and bool(v[1]), budget=45)
    assert rc2 == 0 and par_second, message(
        en=f"From client, http://{ADRESSES['serveur']}:8080/ does not answer ({par_second}). Is the server "
        "listening on 8080, and does the second interface of each Pod carry its address?",
        fr=f"Depuis client, http://{ADRESSES['serveur']}:8080/ ne répond pas ({par_second}). Le serveur "
        "écoute-t-il sur 8080, et la seconde interface de chaque Pod porte-t-elle son adresse ?",
    )
    rc1, par_premier = lire(ip_primaire)
    assert rc1 == 0 and par_premier == par_second, message(
        en=f"Through the cluster network ({ip_primaire}), the server answers {par_premier!r}, and through the "
        f"second network {par_second!r}: the same server must answer on both, and the first network must still "
        "work.",
        fr=f"Par le réseau du cluster ({ip_primaire}), le serveur répond {par_premier!r}, et par le second "
        f"réseau {par_second!r} : le même serveur doit répondre sur les deux, et le premier réseau doit "
        "toujours marcher.",
    )
