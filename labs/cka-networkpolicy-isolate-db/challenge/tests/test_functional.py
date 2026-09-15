"""test_functional.py : cka-networkpolicy-isolate-db

Ces tests lisent l'état du CLUSTER et tentent de vraies connexions, jamais
les commandes tapées.

Quatre affirmations. La première lit la politique : ce qu'elle sélectionne,
ce qu'elle contrôle, ce qu'elle laisse entrer. La deuxième tente la
connexion depuis backend, qui doit passer, et depuis frontend, qui doit
être bloquée : les deux côtés, sinon elle passerait avant le travail. La
troisième tente depuis intrus, au bon label mais dans un autre namespace :
un namespaceSelector vide le laisserait passer. La quatrième vérifie que la
base peut encore résoudre un nom, ce qu'une politique qui contrôlerait
aussi la sortie casserait.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "database"
POLITIQUE = "db-allow-backend"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _connecte(host, namespace: str, pod: str, cible: str) -> bool:
    """Tente une connexion TCP vers la base depuis un Pod, trois secondes au plus."""
    res = _kubectl(host, f"-n {namespace} exec {pod} -- nc -z -w 3 {cible} 5432")
    return res.rc == 0


def _politique(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get networkpolicy {POLITIQUE} -o json")
    assert res.rc == 0, (
        f"Aucune NetworkPolicy {POLITIQUE} dans {NAMESPACE}. Sans politique, tout Pod du cluster "
        "atteint la base."
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. La politique vise la base, contrôle l'entrée, cite le backend et le port.
# ----------------------------------------------------------------------
def test_la_politique_est_ecrite_comme_il_faut(host):
    p = _politique(host)
    assert (p["spec"].get("podSelector") or {}).get("matchLabels", {}).get("app") == "db", (
        f"La politique sélectionne {p['spec'].get('podSelector')} au lieu des Pods app=db. "
        "podSelector désigne les Pods PROTÉGÉS, pas ceux qu'on laisse entrer."
    )
    assert "Ingress" in (p["spec"].get("policyTypes") or []), (
        f"policyTypes vaut {p['spec'].get('policyTypes')} : sans Ingress, rien n'est filtré en entrée."
    )
    regles = p["spec"].get("ingress") or []
    assert regles, "La politique n'a aucune règle ingress : elle bloque tout, backend compris."
    sources = [s for r in regles for s in r.get("from") or []]
    backend = [s for s in sources if (s.get("podSelector") or {}).get("matchLabels", {}).get("app") == "backend"]
    assert backend, f"Aucune source podSelector app=backend dans les règles (sources : {sources})."
    ports = [(pt.get("protocol", "TCP"), pt.get("port")) for r in regles for pt in r.get("ports") or []]
    assert ("TCP", 5432) in ports, (
        f"Les règles ouvrent les ports {ports}, pas TCP 5432. Une règle sans ports ouvre tous les ports."
    )


# ----------------------------------------------------------------------
# 2. Le backend passe, le frontend est bloqué.
# ----------------------------------------------------------------------
def test_le_backend_passe_et_le_frontend_est_bloque(host):
    assert _connecte(host, NAMESPACE, "backend", "db"), (
        "backend n'atteint plus db sur 5432. La politique doit le laisser entrer : podSelector "
        "app=backend dans from, et le port 5432 dans ports."
    )
    assert not _connecte(host, NAMESPACE, "frontend", "db"), (
        "frontend atteint encore db sur 5432. Aucune politique n'isole la base, ou elle ne la "
        "sélectionne pas : dès qu'un Pod est sélectionné en Ingress, tout ce qui n'est pas cité est refusé."
    )


# ----------------------------------------------------------------------
# 3. La preuve : le bon label dans un autre namespace ne suffit pas.
# ----------------------------------------------------------------------
def test_l_intrus_d_un_autre_namespace_est_bloque(host):
    _politique(host)
    assert not _connecte(host, "autre", "intrus", "db.database.svc.cluster.local"), (
        "intrus, dans le namespace autre, atteint db avec son label app=backend. Un podSelector "
        "seul ne vise que le namespace de la politique ; un namespaceSelector vide à côté ouvre "
        "à tous les namespaces, et c'est ce qui laisse entrer intrus."
    )


# ----------------------------------------------------------------------
# 4. La base peut toujours sortir.
# ----------------------------------------------------------------------
def test_la_base_peut_toujours_sortir(host):
    p = _politique(host)
    res = _kubectl(host, f"-n {NAMESPACE} exec db -- nslookup kubernetes.default.svc.cluster.local")
    assert res.rc == 0, (
        f"db ne résout plus kubernetes.default : sa sortie est coupée (policyTypes : "
        f"{p['spec'].get('policyTypes')}). La consigne ne demandait de filtrer que l'entrée ; "
        "contrôler Egress sans règle pour le DNS isole la base de tout, y compris de ce dont "
        "elle a besoin."
    )
