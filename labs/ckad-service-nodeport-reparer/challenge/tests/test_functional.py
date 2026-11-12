"""test_functional.py : ckad-service-nodeport-reparer

Quatre tests, un par état demandé. Ils lisent le Service et ses endpoints, puis
font de vraies requêtes vers le NodePort de CHAQUE nœud, jamais les commandes
tapées.

Un NodePort s'ouvre sur tous les nœuds du cluster, quel que soit l'endroit où
tournent les Pods. Les deux requêtes le vérifient : un Pod qui écouterait
lui-même sur ce port d'un seul nœud (hostPort) répondrait sur ce nœud-là, et pas
sur l'autre.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "guichet"
SERVICE = "accueil"
NODEPORT = 30091
PORT_CONTENEUR = 5678
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

# kube-proxy applique un Service modifié en quelques secondes. On n'attend que
# si le Service porte déjà le bon NodePort.
BUDGET_S = 30
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _objet(host, args: str) -> dict | None:
    res = _kubectl(host, f"{args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _service(host) -> dict:
    return _objet(host, f"-n {NAMESPACE} get service {SERVICE}") or {}


def _adresse(host, noeud: str) -> str:
    n = _objet(host, f"get node {noeud}") or {}
    return next((a["address"] for a in (n.get("status") or {}).get("addresses") or []
                 if a.get("type") == "InternalIP"), "")


def _demander(host, noeud: str) -> tuple[str, str]:
    ip = _adresse(host, noeud)
    corps = host.run(f"curl -s --max-time 4 http://{ip}:{NODEPORT}/").stdout.strip() if ip else ""
    if corps != "accueil" and _nodeport(_service(host)) == NODEPORT:
        fin = time.monotonic() + BUDGET_S
        while corps != "accueil" and time.monotonic() < fin:
            time.sleep(PAS_S)
            corps = host.run(f"curl -s --max-time 4 http://{ip}:{NODEPORT}/").stdout.strip()
    return ip, corps


def _nodeport(svc: dict) -> int | None:
    ports = (svc.get("spec") or {}).get("ports") or []
    return ports[0].get("nodePort") if ports else None


# ----------------------------------------------------------------------
# 1. Le Service est de type NodePort, sur le port demandé.
# ----------------------------------------------------------------------
def test_le_service_est_nodeport_sur_30091(host):
    svc = _service(host)
    assert svc, message(
        en=f"No Service {SERVICE} in {NAMESPACE}.",
        fr=f"Aucun Service {SERVICE} dans {NAMESPACE}.",
    )
    genre = svc["spec"].get("type")
    port = _nodeport(svc)
    assert genre == "NodePort" and port == NODEPORT, message(
        en=f"{SERVICE} is of type {genre}, NodePort {port}. Expected type NodePort on port {NODEPORT}: without a "
        "declared value, Kubernetes draws one at random, and the address given to users changes each time the "
        "Service is recreated.",
        fr=f"{SERVICE} est de type {genre}, NodePort {port}. Attendu le type NodePort sur le port {NODEPORT} : sans "
        "valeur déclarée, Kubernetes en tire une au hasard, et l'adresse donnée aux utilisateurs change à chaque "
        "recréation du Service.",
    )


# ----------------------------------------------------------------------
# 2. Ses endpoints sont les Pods d'accueil, sur le port du conteneur.
# ----------------------------------------------------------------------
def test_les_endpoints_sont_les_pods_d_accueil(host):
    tranches = _objet(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}") or {}
    pods = set(_kubectl(host, f"-n {NAMESPACE} get pods -l app=accueil -o jsonpath='{{.items[*].metadata.name}}'")
               .stdout.split())
    vises, ports = set(), set()
    for t in tranches.get("items", []):
        for e in t.get("endpoints") or []:
            if (e.get("conditions") or {}).get("ready"):
                vises.add((e.get("targetRef") or {}).get("name"))
        for p in t.get("ports") or []:
            ports.add(p.get("port"))
    ok = bool(pods) and vises == pods and ports == {PORT_CONTENEUR}
    assert ok, message(
        en=f"{SERVICE} sends to {sorted(v for v in vises if v) or 'no Pod'} on port(s) "
        f"{sorted(p for p in ports if p) or 'none'}. Expected the ready Pods of the accueil Deployment "
        f"({sorted(pods)}), on the port their container listens on.",
        fr=f"{SERVICE} envoie vers {sorted(v for v in vises if v) or 'aucun Pod'} sur le(s) port(s) "
        f"{sorted(p for p in ports if p) or 'aucun'}. Attendu les Pods prêts du Deployment accueil "
        f"({sorted(pods)}), sur le port où leur conteneur écoute.",
    )


# ----------------------------------------------------------------------
# 3. et 4. Le NodePort répond sur chaque nœud.
# ----------------------------------------------------------------------
def test_le_control_plane_sert_accueil_sur_30091(host):
    ip, corps = _demander(host, "k8s-cp.lab")
    assert corps == "accueil", message(
        en=f"http://{ip}:{NODEPORT}/ on the control plane answers {corps or 'nothing'!r} instead of \"accueil\".",
        fr=f"http://{ip}:{NODEPORT}/ sur le control plane répond {corps or 'rien'!r} au lieu de « accueil ».",
    )


def test_le_worker_sert_accueil_sur_30091(host):
    ip, corps = _demander(host, "k8s-w1.lab")
    assert corps == "accueil", message(
        en=f"http://{ip}:{NODEPORT}/ on the worker answers {corps or 'nothing'!r} instead of \"accueil\". A "
        "NodePort opens on every node of the cluster, wherever the Pods run.",
        fr=f"http://{ip}:{NODEPORT}/ sur le worker répond {corps or 'rien'!r} au lieu de « accueil ». Un NodePort "
        "s'ouvre sur tous les nœuds du cluster, où que tournent les Pods.",
    )
