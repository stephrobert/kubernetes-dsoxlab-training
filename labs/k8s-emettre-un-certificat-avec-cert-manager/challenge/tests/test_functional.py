"""test_functional.py : k8s-emettre-un-certificat-avec-cert-manager

1. l'Issuer auto-signe est de type selfSigned et prêt ;
2. le Certificate ca-interne est un certificat d'autorité (isCA), émis par
   auto-signe et prêt, et l'Issuer ca-interne, de type CA, est prêt ;
3. le Certificate vitrine-tls est prêt, pour vitrine.atelier-tls.svc, émis par
   ca-interne, et son certificat se vérifie contre la CA interne ;
4. le Certificate api-tls, cassé au départ, est prêt, émis par ca-interne, et
   se vérifie contre la CA interne.

La chaîne se juge par openssl verify, pas par la seule condition Ready : un
certificat signé par le mauvais émetteur peut être Ready.

Les quatre échouent sur l'état de départ : aucun émetteur, api-tls not ready.
"""

from __future__ import annotations

import base64
import json

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS = "atelier-tls"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict:
    res = host.run(f"{KUBECTL} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else {}


def _pret(objet: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (objet.get("status") or {}).get("conditions") or [])


def _secret(host, nom: str, cle: str) -> str:
    valeur = ((_json(host, f"get secret {nom}").get("data")) or {}).get(cle, "")
    return base64.b64decode(valeur).decode() if valeur else ""


def _verifie(host, certificat: str, ca: str) -> bool:
    """openssl verify du certificat contre la CA, l'un et l'autre en PEM."""
    if not certificat or not ca:
        return False
    b = lambda t: base64.b64encode(t.encode()).decode()  # noqa: E731
    commande = (f"T=$(mktemp -d); echo {b(ca)} | base64 -d > $T/ca.pem; echo {b(certificat)} | base64 -d > $T/c.pem; "
                "openssl verify -CAfile $T/ca.pem $T/c.pem; r=$?; rm -rf $T; exit $r")
    return host.run(commande).rc == 0


def _ca_interne(host) -> str:
    return _secret(host, "ca-interne", "tls.crt")


def test_l_emetteur_auto_signe_est_pret(host):
    emetteur = _json(host, "get issuer auto-signe")
    assert "selfSigned" in (emetteur.get("spec") or {}) and _pret(emetteur), message(
        en=f"No ready self-signed Issuer named auto-signe in {NS}.",
        fr=f"Aucun Issuer auto-signé prêt nommé auto-signe dans {NS}.",
    )


def test_la_ca_interne_est_prete(host):
    cert = _json(host, "get certificate ca-interne")
    spec = cert.get("spec") or {}
    emetteur = _json(host, "get issuer ca-interne")
    ca = _ca_interne(host)
    est_une_ca = host.run(f"echo {base64.b64encode(ca.encode()).decode()} | base64 -d | openssl x509 -noout -text "
                          "| grep -q 'CA:TRUE'").rc == 0 if ca else False
    ok = (spec.get("isCA") is True and (spec.get("issuerRef") or {}).get("name") == "auto-signe" and _pret(cert)
          and ((emetteur.get("spec") or {}).get("ca") or {}).get("secretName") == "ca-interne" and _pret(emetteur)
          and est_une_ca)
    assert ok, message(
        en="The internal CA is not ready: expected a Certificate ca-interne with isCA, issued by auto-signe and "
        "ready, a CA certificate in its Secret, and a ready Issuer ca-interne of type CA on that Secret.",
        fr="La CA interne n'est pas prête : attendu un Certificate ca-interne avec isCA, émis par auto-signe et "
        "prêt, un certificat d'autorité dans son Secret, et un Issuer ca-interne de type CA, prêt, sur ce Secret.",
    )


def test_le_certificat_de_la_vitrine_est_signe_par_la_ca_interne(host):
    cert = _json(host, "get certificate vitrine-tls")
    spec = cert.get("spec") or {}
    chaine = _verifie(host, _secret(host, spec.get("secretName") or "vitrine-tls", "tls.crt"), _ca_interne(host))
    ok = (_pret(cert) and "vitrine.atelier-tls.svc" in (spec.get("dnsNames") or [])
          and (spec.get("issuerRef") or {}).get("name") == "ca-interne" and chaine)
    assert ok, message(
        en="The certificate vitrine-tls is not as expected: ready, for vitrine.atelier-tls.svc, issued by the "
        "Issuer ca-interne, with a chain that openssl verify accepts against the internal CA.",
        fr="Le certificat vitrine-tls n'est pas conforme : prêt, pour vitrine.atelier-tls.svc, émis par l'Issuer "
        "ca-interne, avec une chaîne qu'openssl verify accepte contre la CA interne.",
    )


def test_le_certificat_api_est_repare(host):
    cert = _json(host, "get certificate api-tls")
    spec = cert.get("spec") or {}
    chaine = _verifie(host, _secret(host, "api-tls", "tls.crt"), _ca_interne(host))
    ok = (_pret(cert) and (spec.get("issuerRef") or {}).get("name") == "ca-interne"
          and "api.atelier-tls.svc" in (spec.get("dnsNames") or []) and chaine)
    raison = next((c.get("message", "") for c in (cert.get("status") or {}).get("conditions") or []
                   if c.get("type") == "Ready"), "")
    assert ok, message(
        en=f"The certificate api-tls is not repaired (Ready says: {raison[:140]!r}). It must be ready, for "
        "api.atelier-tls.svc, issued by the internal CA, and its chain must lead to it.",
        fr=f"Le certificat api-tls n'est pas réparé (Ready dit : {raison[:140]!r}). Il doit être prêt, pour "
        "api.atelier-tls.svc, émis par la CA interne, et sa chaîne doit y mener.",
    )
