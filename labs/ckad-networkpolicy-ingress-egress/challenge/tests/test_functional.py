"""test_functional.py : ckad-networkpolicy-ingress-egress

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées, et ils
font de vraies connexions entre Pods : c'est le CNI qui applique les règles,
et c'est lui qu'on interroge.

Chaque test vérifie un flux qui doit passer ET un flux qui doit être bloqué.
Sans politique, tout passe : un test qui ne vérifierait que le flux permis
passerait avant le travail, et ne mesurerait rien.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _ip(host, pod: str) -> str:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {pod} -o jsonpath='{{.status.podIP}}'")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"Pod {pod} has no address: setup had placed it there.",
        fr=f"Le Pod {pod} n'a pas d'adresse : le setup l'avait posé.",
    )
    return res.stdout.strip()


def _http(host, depuis: str, vers: str) -> bool:
    """Une requête HTTP de Pod à Pod, trois secondes de patience."""
    res = _kubectl(host, f"-n {NAMESPACE} exec {depuis} -- wget -qO- -T 3 http://{_ip(host, vers)}/")
    return res.rc == 0 and vers in res.stdout


def _dns(host, depuis: str) -> bool:
    res = _kubectl(host, f"-n {NAMESPACE} exec {depuis} -- nslookup kubernetes.default.svc.cluster.local")
    return res.rc == 0


def _politique(host, nom: str) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get networkpolicy {nom} -o json")
    assert res.rc == 0, message(
        en=f"No NetworkPolicy {nom} in {NAMESPACE}.",
        fr=f"Aucune NetworkPolicy {nom} dans {NAMESPACE}.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Les deux politiques existent et visent les bons Pods.
# ----------------------------------------------------------------------
def test_les_politiques_visent_les_bons_tiers(host):
    for nom, tier in (("backend-policy", "backend"), ("database-policy", "database")):
        p = _politique(host, nom)
        selecteur = (p["spec"].get("podSelector") or {}).get("matchLabels") or {}
        assert selecteur.get("tier") == tier, message(
            en=f"{nom} selects {selecteur}, expected tier={tier}.",
            fr=f"{nom} sélectionne {selecteur}, attendu tier={tier}.",
        )
        types = p["spec"].get("policyTypes") or ["Ingress"]
        assert "Ingress" in types and "Egress" in types, message(
            en=f"{nom} declares policyTypes {types}: both Ingress AND Egress are needed, otherwise "
            "the missing direction is not restricted at all.",
            fr=f"{nom} déclare policyTypes {types} : il faut Ingress ET Egress, sinon la "
            "direction absente n'est pas restreinte du tout.",
        )


# ----------------------------------------------------------------------
# 2. Le backend n'accepte que le frontend.
# ----------------------------------------------------------------------
def test_le_backend_n_accepte_que_le_frontend(host):
    assert _http(host, "frontend", "backend"), message(
        en="frontend no longer reaches backend on port 80: the ingress rule of "
        "backend-policy must allow tier=frontend Pods on that port.",
        fr="frontend ne joint plus backend sur le port 80 : la règle ingress de "
        "backend-policy doit autoriser les Pods tier=frontend sur ce port.",
    )
    assert not _http(host, "intrus", "backend"), message(
        en="intrus reaches backend: nothing blocks it. backend-policy must exist, "
        "select tier=backend, and allow only tier=frontend inbound.",
        fr="intrus joint backend : rien ne le bloque. backend-policy doit exister, "
        "sélectionner tier=backend, et n'autoriser en entrée que tier=frontend.",
    )


# ----------------------------------------------------------------------
# 3. Le backend sort vers la base et le DNS, et la base n'accepte que lui.
# ----------------------------------------------------------------------
def test_le_backend_parle_a_la_base_et_resout_des_noms(host):
    assert _http(host, "backend", "database"), message(
        en="backend no longer reaches database: the egress rule of backend-policy must "
        "allow tier=database on port 80, and the ingress rule of "
        "database-policy must accept tier=backend.",
        fr="backend ne joint plus database : la règle egress de backend-policy doit "
        "autoriser tier=database sur le port 80, et la règle ingress de "
        "database-policy doit accepter tier=backend.",
    )
    assert _dns(host, "backend"), message(
        en="backend no longer resolves any name: its egress is restricted and DNS is "
        "not allowed. The resolver is in kube-system, port 53, UDP and TCP.",
        fr="backend ne résout plus aucun nom : sa sortie est restreinte et le DNS n'est "
        "pas autorisé. Le résolveur est dans kube-system, port 53, UDP et TCP.",
    )
    assert not _http(host, "intrus", "database"), message(
        en="intrus reaches database: database-policy must accept only tier=backend inbound.",
        fr="intrus joint database : database-policy doit n'accepter en entrée que tier=backend.",
    )


# ----------------------------------------------------------------------
# 4. La base ne parle à personne, pas même au DNS.
# ----------------------------------------------------------------------
def test_la_base_ne_sort_pas(host):
    assert not _http(host, "database", "backend"), message(
        en="database reaches backend: its egress is not forbidden. Declaring Egress "
        "in policyTypes with no egress rule forbids all outbound traffic.",
        fr="database joint backend : sa sortie n'est pas interdite. Déclarer Egress "
        "dans policyTypes sans aucune règle egress interdit toute sortie.",
    )
    assert not _dns(host, "database"), message(
        en="database resolves names: its egress towards DNS is still allowed, so its "
        "egress is not entirely forbidden.",
        fr="database résout des noms : sa sortie vers le DNS reste permise, donc sa "
        "sortie n'est pas entièrement interdite.",
    )
