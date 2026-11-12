"""test_functional.py : cks-ingress-tls

Ces tests lisent le Secret, l'Ingress et la connexion TLS elle-même, jamais les
commandes tapées. Un test vérifie un seul état.

Le piège de ce lab est qu'un test naïf serait vert avant le travail. Mesuré le
2026-09-16 : sans aucune section TLS, le contrôleur répond quand même 200 en
HTTPS, avec un certificat auto-signé générique qu'il fabrique au démarrage,
`CN = TRAEFIK DEFAULT CERT`. « Le site répond en HTTPS » ne mesure donc rien.
Le dernier test exige une réponse en HTTPS VÉRIFIÉ, contre le certificat que
l'apprenant a déposé : le certificat par défaut ne la donne jamais.

Tous échouent avant le travail : aucun Secret TLS, aucune section tls dans
l'Ingress. Une attente ne s'ouvre que si l'Ingress déclare déjà du TLS.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "vitrine"
INGRESS = "site"
HOTE = "vitrine.lab"
PORT_TLS = 30443
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
CERT_PAR_DEFAUT = "TRAEFIK DEFAULT CERT"

# Le contrôleur recharge sa configuration après notification : la bascule
# n'est pas immédiate.
ATTENTE = 60
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _secrets_tls(host) -> list[dict]:
    return [s for s in (_json(host, f"-n {NAMESPACE} get secrets") or {}).get("items", [])
            if s.get("type") == "kubernetes.io/tls" and {"tls.crt", "tls.key"} <= set(s.get("data") or {})]


def _tls_de_l_ingress(host) -> list[dict]:
    ing = _json(host, f"-n {NAMESPACE} get ingress {INGRESS}") or {}
    return [t for t in (ing.get("spec") or {}).get("tls") or [] if HOTE in (t.get("hosts") or [])]


def _certificat_presente(host) -> str:
    """Le sujet et le subjectAltName du certificat servi pour l'hôte (SNI)."""
    return host.run(
        f"echo | openssl s_client -connect 127.0.0.1:{PORT_TLS} -servername {HOTE} 2>/dev/null "
        "| openssl x509 -noout -subject -ext subjectAltName"
    ).stdout.strip()


# ----------------------------------------------------------------------
# 1. Le certificat est déposé dans un Secret du bon type.
# ----------------------------------------------------------------------
def test_le_certificat_est_depose_dans_un_secret_tls(host):
    presents = {s["metadata"]["name"]: s.get("type")
                for s in (_json(host, f"-n {NAMESPACE} get secrets") or {}).get("items", [])}
    assert _secrets_tls(host), message(
        en=f"No Secret of type kubernetes.io/tls carrying tls.crt and tls.key in {NAMESPACE} (present: "
        f"{presents or 'none'}). The TYPE matters: the controller selects on it.",
        fr=f"Aucun Secret de type kubernetes.io/tls portant tls.crt et tls.key dans {NAMESPACE} (présents : "
        f"{presents or 'aucun'}). Le TYPE compte : le contrôleur sélectionne sur lui.",
    )


# ----------------------------------------------------------------------
# 2. L'Ingress déclare le TLS de l'hôte, avec ce Secret.
# ----------------------------------------------------------------------
def test_l_ingress_declare_le_tls_de_l_hote_avec_ce_secret(host):
    noms = {s["metadata"]["name"] for s in _secrets_tls(host)}
    declares = [t.get("secretName") for t in _tls_de_l_ingress(host)]
    assert any(n in noms for n in declares), message(
        en=f"The Ingress {INGRESS} declares TLS for {HOTE} with {declares or 'no Secret'}; the TLS Secrets of "
        f"{NAMESPACE} are {sorted(noms) or 'none'}. A Secret no Ingress names is served to nobody.",
        fr=f"L'Ingress {INGRESS} déclare le TLS de {HOTE} avec {declares or 'aucun Secret'} ; les Secrets TLS de "
        f"{NAMESPACE} sont {sorted(noms) or 'aucun'}. Un Secret qu'aucun Ingress ne nomme n'est servi à personne.",
    )


# ----------------------------------------------------------------------
# 3. Le serveur présente un certificat qui nomme l'hôte.
# ----------------------------------------------------------------------
def test_le_serveur_presente_un_certificat_qui_nomme_l_hote(host):
    sujet = _certificat_presente(host)
    fin = time.monotonic() + (ATTENTE if _tls_de_l_ingress(host) else 0)
    while (CERT_PAR_DEFAUT in sujet or f"DNS:{HOTE}" not in sujet) and time.monotonic() < fin:
        time.sleep(PAS)
        sujet = _certificat_presente(host)
    assert sujet and CERT_PAR_DEFAUT not in sujet and f"DNS:{HOTE}" in sujet, message(
        en=f"For {HOTE}, the server presents: {sujet or 'no certificate'!r}. Expected a certificate whose "
        f"subjectAltName names {HOTE}, not the default certificate of the controller. Browsers ignore the CN, and curl only falls back on it.",
        fr=f"Pour {HOTE}, le serveur présente : {sujet or 'aucun certificat'!r}. Attendu un certificat dont le "
        f"subjectAltName nomme {HOTE}, et non le certificat par défaut du contrôleur. Les navigateurs ignorent le CN, et curl ne s'y rabat que par défaut.",
    )


# ----------------------------------------------------------------------
# 4. Le site répond en HTTPS vérifié contre ce certificat.
# ----------------------------------------------------------------------
def test_le_site_repond_en_https_verifie(host):
    noms = {s["metadata"]["name"]: s for s in _secrets_tls(host)}
    declares = [t.get("secretName") for t in _tls_de_l_ingress(host) if t.get("secretName") in noms]
    if not declares:
        pytest.fail(message(
            en=f"No TLS Secret is declared for {HOTE}: nothing to verify the site against.",
            fr=f"Aucun Secret TLS n'est déclaré pour {HOTE} : rien contre quoi vérifier le site.",
        ))
    encode = noms[declares[0]]["data"]["tls.crt"]
    base64.b64decode(encode, validate=True)
    chemin = "/tmp/dsoxlab-cks-ingress-tls.crt"  # noqa: S108 -- fichier jetable du test, sur le nœud
    host.run(f"echo {encode} | base64 -d > {chemin}")
    code = ""
    fin = time.monotonic() + ATTENTE
    while time.monotonic() < fin:
        code = host.run(
            f"curl -s -o /dev/null -w '%{{http_code}}' --cacert {chemin} "
            f"--resolve {HOTE}:{PORT_TLS}:127.0.0.1 https://{HOTE}:{PORT_TLS}/ --max-time 10"
        ).stdout.strip()
        if code == "200":
            break
        time.sleep(PAS)
    host.run(f"rm -f {chemin}")
    assert code == "200", message(
        en=f"A client that trusts your certificate gets {code or 'no answer'!r} from https://{HOTE}. Expected 200: "
        "the certificate served must verify for this host, and the route must still lead to the site.",
        fr=f"Un client qui fait confiance à votre certificat obtient {code or 'aucune réponse'!r} de "
        f"https://{HOTE}. Attendu 200 : le certificat servi doit se vérifier pour cet hôte, et la route mener "
        "encore au site.",
    )
