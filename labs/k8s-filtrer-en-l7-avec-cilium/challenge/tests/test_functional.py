"""test_functional.py : k8s-filtrer-en-l7-avec-cilium

Quatre tests, un par état demandé. Ils lisent le cluster et font passer de
vraies requêtes, par le Gateway et depuis le Pod lecteur ; jamais un fichier
de l'apprenant.

Pourquoi le test 4 est distinct du test 3 : une politique L7 qui n'autorise
que lecteur coupe aussi le Gateway, dont le trafic arrive avec l'identité
réservée « ingress » de Cilium (mesuré le 2026-11-18 : curl par le Gateway
rend 000). Le test 3 peut donc être vert pendant que le Gateway est coupé.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "catalogue"
HOTE = "fiches.formation.test"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
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
    return json.loads(sortie) if rc == 0 and sortie else {}


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _condition(conditions: list | None, type_: str) -> tuple[str, str]:
    for c in conditions or []:
        if c.get("type") == type_:
            return c.get("status", ""), c.get("reason", "")
    return "", ""


def _gateway(host) -> dict:
    """Le Gateway de classe cilium de catalogue qui porte un listener HTTP sur 80."""
    for gw in _json(host, f"-n {NS} get gateways.gateway.networking.k8s.io").get("items", []):
        spec = gw.get("spec", {})
        if spec.get("gatewayClassName") == "cilium" and any(
            ln.get("protocol") == "HTTP" and ln.get("port") == 80 for ln in spec.get("listeners") or []
        ):
            return gw
    return {}


def _adresse(host) -> str:
    adresses = _gateway(host).get("status", {}).get("addresses") or []
    return adresses[0].get("value", "") if adresses else ""


def _adresse_requise(host) -> str:
    ip = _adresse(host)
    if not ip:
        pytest.fail(message(
            en="No Gateway of class cilium with an address in catalogue: the first test says why.",
            fr="Aucun Gateway de classe cilium avec une adresse dans catalogue : le premier test dit pourquoi.",
        ))
    return ip


def _par_le_gateway(host, ip: str, methode: str = "GET") -> tuple[str, str]:
    """(code, corps) d'une requête HTTP par le Gateway, avec le nom du lab."""
    res = host.run(f"curl -s -m 8 -X {methode} -H 'Host: {HOTE}' http://{ip}/ -w '|%{{http_code}}'")
    corps, _, code = res.stdout.rpartition("|")
    return code.strip(), corps.strip()


def _depuis_lecteur(host, methode: str = "GET") -> str:
    res = host.run(
        f"sudo {KUBECTL} -n {NS} exec lecteur -- curl -s -m 5 -o /dev/null -X {methode} "
        "-w '%{http_code}' http://fiches/"
    )
    return res.stdout.strip()


# ----------------------------------------------------------------------
# 1. Un Gateway servi par Cilium est programmé, avec une adresse.
# ----------------------------------------------------------------------
def test_un_gateway_cilium_est_programme(host):
    gw = _attendre(lambda: _gateway(host), lambda g: _condition(
        g.get("status", {}).get("conditions"), "Programmed")[0] == "True")
    assert gw, message(
        en=f"No Gateway of class cilium with an HTTP listener on port 80 in {NS}. Is the GatewayClass cilium "
        "there? It appears once the Gateway API CRDs are installed and Cilium's Gateway API is turned on.",
        fr=f"Aucun Gateway de classe cilium avec un listener HTTP sur le port 80 dans {NS}. La GatewayClass "
        "cilium existe-t-elle ? Elle apparaît une fois les CRD de la Gateway API installées et la Gateway API "
        "de Cilium activée.",
    )
    statut, raison = _condition(gw.get("status", {}).get("conditions"), "Programmed")
    assert statut == "True" and _adresse(host), message(
        en=f"The Gateway {gw['metadata']['name']} is not programmed: Programmed={statut or 'absent'} "
        f"({raison or 'no reason'}). AddressNotAssigned means it waits for a load balancer address this "
        "cluster doesn't have: Cilium can give one from a pool.",
        fr=f"Le Gateway {gw['metadata']['name']} n'est pas programmé : Programmed={statut or 'absent'} "
        f"({raison or 'sans raison'}). AddressNotAssigned veut dire qu'il attend une adresse de répartiteur "
        "que ce cluster n'a pas : Cilium peut en donner une depuis un pool.",
    )


# ----------------------------------------------------------------------
# 2. Le nom du lab mène à l'application fiches.
# ----------------------------------------------------------------------
def test_la_route_mene_aux_fiches(host):
    ip = _adresse_requise(host)
    code, corps = _attendre(lambda: _par_le_gateway(host, ip), lambda v: v[1] == "fiches", budget=60)
    assert corps == "fiches", message(
        en=f"http://{HOTE}/ through the Gateway ({ip}) answers code {code or 'none'}, body {corps!r}: a route "
        "attached to the Gateway must send this name to the Service fiches.",
        fr=f"http://{HOTE}/ par le Gateway ({ip}) répond le code {code or 'aucun'}, corps {corps!r} : une "
        "route attachée au Gateway doit envoyer ce nom vers le Service fiches.",
    )


# ----------------------------------------------------------------------
# 3. lecteur lit sans écrire.
# ----------------------------------------------------------------------
def test_lecteur_lit_sans_ecrire(host):
    lecture = _attendre(lambda: _depuis_lecteur(host), lambda v: v == "200", budget=45)
    ecriture = _depuis_lecteur(host, "POST")
    assert lecture == "200" and ecriture == "403", message(
        en=f"From lecteur, GET / answers {lecture or 'nothing'} and POST / answers {ecriture or 'nothing'}: "
        "expected 200 and 403. A Cilium policy with http rules (method, path) refuses at the HTTP level.",
        fr=f"Depuis lecteur, GET / répond {lecture or 'rien'} et POST / répond {ecriture or 'rien'} : attendu "
        "200 et 403. Une politique Cilium à règles http (méthode, chemin) refuse au niveau HTTP.",
    )


# ----------------------------------------------------------------------
# 4. Par le Gateway aussi, GET passe et POST est refusé.
# ----------------------------------------------------------------------
def test_par_le_gateway_get_passe_et_post_est_refuse(host):
    ip = _adresse_requise(host)
    get = _attendre(lambda: _par_le_gateway(host, ip), lambda v: v[0] == "200", budget=45)
    assert get[0] == "200", message(
        en=f"GET / through the Gateway answers {get[0] or 'nothing'}. If it worked before your policy, the "
        "policy also cuts the Gateway: its traffic arrives with Cilium's reserved identity ingress, to allow "
        "as an entity.",
        fr=f"GET / par le Gateway répond {get[0] or 'rien'}. Si ça marchait avant votre politique, elle coupe "
        "aussi le Gateway : son trafic arrive avec l'identité réservée ingress de Cilium, à autoriser comme "
        "une entité.",
    )
    post = _par_le_gateway(host, ip, "POST")
    assert post[0] == "403", message(
        en=f"POST / through the Gateway answers {post[0] or 'nothing'}, expected 403: the http rules must "
        "apply to the Gateway's traffic too.",
        fr=f"POST / par le Gateway répond {post[0] or 'rien'}, attendu 403 : les règles http doivent "
        "s'appliquer au trafic du Gateway aussi.",
    )
