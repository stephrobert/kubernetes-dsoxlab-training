"""test_functional.py : cka-troubleshoot-networking

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. Les trois premières lisent le Service et les politiques ;
la quatrième fait une vraie requête depuis le Pod client, et c'est elle qui
prouve que le trafic passe. Elle n'a de sens que parce que le CNI applique
les NetworkPolicy : sur Flannel, block-all n'aurait rien bloqué.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
SERVICE = "web-svc"
CLIENT = "client"
POLITIQUE = "allow-web-ingress"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, f"kubectl {args} : {res.stderr.strip()[:200]}"
    return json.loads(res.stdout)


def _endpoints_prets(host) -> list[str]:
    tranches = _json(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}")
    return [
        adresse
        for t in tranches["items"]
        for e in t.get("endpoints") or []
        for adresse in e.get("addresses") or []
        if (e.get("conditions") or {}).get("ready")
    ]


# ----------------------------------------------------------------------
# 1. Le Service a des endpoints : son selector trouve les Pods.
# ----------------------------------------------------------------------
def test_le_service_a_des_endpoints(host):
    service = _json(host, f"-n {NAMESPACE} get service {SERVICE}")
    prets = _endpoints_prets(host)
    assert prets, (
        f"Le Service {SERVICE} n'a aucun endpoint prêt. Son selector est "
        f"{service['spec'].get('selector')} : aucun Pod ne porte ces labels. "
        "Comparez kubectl describe service et kubectl get pods --show-labels."
    )


# ----------------------------------------------------------------------
# 2. Le Service vise le port où nginx écoute.
# ----------------------------------------------------------------------
def test_le_service_vise_le_bon_port(host):
    service = _json(host, f"-n {NAMESPACE} get service {SERVICE}")
    ports = service["spec"].get("ports") or []
    cibles = [str(p.get("targetPort", p.get("port"))) for p in ports]
    assert "80" in cibles, (
        f"Le Service {SERVICE} transmet vers targetPort {cibles} : nginx écoute "
        "sur 80. Des endpoints existent, mais chaque requête part vers un port "
        "où personne ne répond."
    )


# ----------------------------------------------------------------------
# 3. La politique rouvre exactement le port 80 des Pods web, et block-all reste.
# ----------------------------------------------------------------------
def test_la_politique_rouvre_le_web_sans_retirer_block_all(host):
    res = _kubectl(host, f"-n {NAMESPACE} get networkpolicy block-all")
    assert res.rc == 0, (
        "La politique block-all a disparu. Elle est voulue par la sécurité et "
        "devait rester : les politiques s'additionnent, une seconde suffit à "
        "rouvrir un port."
    )
    res = _kubectl(host, f"-n {NAMESPACE} get networkpolicy {POLITIQUE} -o json")
    assert res.rc == 0, (
        f"Aucune NetworkPolicy {POLITIQUE} dans {NAMESPACE}. Tant que seule "
        "block-all existe, aucun trafic n'entre vers les Pods du namespace."
    )
    politique = json.loads(res.stdout)
    selecteur = (politique["spec"].get("podSelector") or {}).get("matchLabels") or {}
    assert selecteur.get("app") == "web", (
        f"{POLITIQUE} sélectionne {selecteur or 'tous les Pods'} : elle doit "
        "viser les Pods app=web, pas tout le namespace."
    )
    assert "Ingress" in (politique["spec"].get("policyTypes") or ["Ingress"]), (
        f"{POLITIQUE} ne porte pas sur l'Ingress : c'est le trafic entrant que block-all ferme."
    )
    ports = [
        str(p.get("port")) for regle in politique["spec"].get("ingress") or []
        for p in regle.get("ports") or []
    ]
    assert "80" in ports, (
        f"{POLITIQUE} n'ouvre pas le port 80 : ports déclarés {ports or 'aucun'}. "
        "Une règle ingress sans ports ouvrirait tout ; il faut le port 80, TCP."
    )


# ----------------------------------------------------------------------
# 4. La preuve qui compte : le client joint le Service par son nom.
# ----------------------------------------------------------------------
def test_le_client_joint_le_service(host):
    res = _kubectl(host, f"-n {NAMESPACE} exec {CLIENT} -- wget -qO- -T 5 http://{SERVICE}/")
    if res.rc != 0:
        assert _endpoints_prets(host), (
            f"http://{SERVICE}/ ne répond pas, et le Service n'a aucun endpoint : "
            "commencez par le selector, les tests précédents disent quoi regarder."
        )
        pytest.fail(
            f"Le Service a des endpoints, mais http://{SERVICE}/ ne répond pas "
            "depuis le client. Reste le port, ou une politique réseau qui bloque "
            f"encore le trafic entrant vers les Pods web. Sortie : {res.stderr.strip()[:200]}"
        )
    assert "nginx" in res.stdout.lower(), (
        f"Quelque chose répond sur http://{SERVICE}/ mais ce n'est pas nginx : "
        f"{res.stdout[:120]!r}"
    )
