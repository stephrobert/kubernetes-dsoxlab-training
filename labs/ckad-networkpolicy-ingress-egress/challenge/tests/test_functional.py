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
# 1. et 2. Chaque politique vise son tier, dans les deux directions.
# ----------------------------------------------------------------------
def _vise_son_tier(host, nom: str, tier: str) -> None:
    p = _politique(host, nom)
    selecteur = (p["spec"].get("podSelector") or {}).get("matchLabels") or {}
    types = p["spec"].get("policyTypes") or ["Ingress"]
    assert selecteur.get("tier") == tier and "Ingress" in types and "Egress" in types, message(
        en=f"{nom} selects {selecteur} and declares policyTypes {types}. Expected tier={tier}, with both Ingress "
        "AND Egress: a missing direction is not restricted at all.",
        fr=f"{nom} sélectionne {selecteur} et déclare policyTypes {types}. Attendu tier={tier}, avec Ingress ET "
        "Egress : une direction absente n'est pas restreinte du tout.",
    )


def test_backend_policy_vise_le_backend_dans_les_deux_sens(host):
    _vise_son_tier(host, "backend-policy", "backend")


def test_database_policy_vise_la_base_dans_les_deux_sens(host):
    _vise_son_tier(host, "database-policy", "database")


# ----------------------------------------------------------------------
# 3. Le backend n'accepte que le frontend.
# ----------------------------------------------------------------------
def test_le_backend_n_accepte_que_le_frontend(host):
    joint = _http(host, "frontend", "backend")
    intrus = _http(host, "intrus", "backend")
    assert joint and not intrus, message(
        en=f"frontend {'reaches' if joint else 'does not reach'} backend, intrus "
        f"{'reaches' if intrus else 'does not reach'} it. Expected frontend allowed on port 80, intrus refused.",
        fr=f"frontend {'joint' if joint else 'ne joint pas'} backend, intrus {'le joint' if intrus else 'ne le joint pas'}"
        ". Attendu frontend autorisé sur le port 80, intrus refusé.",
    )


# ----------------------------------------------------------------------
# 4. Le backend ne sort que vers la base et vers le DNS.
# ----------------------------------------------------------------------
def test_le_backend_joint_la_base_et_resout_des_noms(host):
    base = _http(host, "backend", "database")
    dns = _dns(host, "backend")
    ailleurs = _http(host, "backend", "intrus")
    assert base and dns and not ailleurs, message(
        en=f"backend {'reaches' if base else 'does not reach'} database, {'resolves' if dns else 'does not resolve'} "
        f"names, and {'reaches' if ailleurs else 'does not reach'} intrus. Expected database and DNS allowed, "
        "everything else refused: its egress allows tier=database on port 80 and the cluster DNS (kube-system, "
        "port 53, UDP and TCP), and nothing more.",
        fr=f"backend {'joint' if base else 'ne joint pas'} database, {'résout' if dns else 'ne résout pas'} les noms, "
        f"et {'joint' if ailleurs else 'ne joint pas'} intrus. Attendu la base et le DNS autorisés, tout le reste "
        "refusé : sa sortie autorise tier=database sur le port 80 et le DNS du cluster (kube-system, port 53, UDP "
        "et TCP), rien de plus.",
    )


# ----------------------------------------------------------------------
# 5. La base n'accepte que le backend.
# ----------------------------------------------------------------------
def test_la_base_refuse_l_intrus(host):
    assert not _http(host, "intrus", "database"), message(
        en="intrus reaches database: database-policy must accept only tier=backend inbound.",
        fr="intrus joint database : database-policy doit n'accepter en entrée que tier=backend.",
    )


# ----------------------------------------------------------------------
# 6. La base ne parle à personne, pas même au DNS.
# ----------------------------------------------------------------------
def test_la_base_ne_sort_pas(host):
    sort = _http(host, "database", "backend")
    dns = _dns(host, "database")
    assert not sort and not dns, message(
        en=f"database {'reaches' if sort else 'does not reach'} backend and {'resolves' if dns else 'does not resolve'} "
        "names. Expected neither: declaring Egress in policyTypes with no egress rule forbids all outbound traffic.",
        fr=f"database {'joint' if sort else 'ne joint pas'} backend et {'résout' if dns else 'ne résout pas'} les noms. "
        "Attendu ni l'un ni l'autre : déclarer Egress dans policyTypes sans règle egress interdit toute sortie.",
    )
