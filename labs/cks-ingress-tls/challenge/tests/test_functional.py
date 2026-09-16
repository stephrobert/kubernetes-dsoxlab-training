"""test_functional.py : cks-ingress-tls

Deux affirmations qui lisent l'état réel de la connexion TLS, jamais les
commandes tapées.

Le piège de ce lab est qu'un test naïf serait vert avant le travail. Mesuré le
2026-09-16 : sans aucune section TLS, le contrôleur répond quand même 200 en
HTTPS, avec un certificat auto-signé générique qu'il fabrique au démarrage,
`CN = TRAEFIK DEFAULT CERT`. « Le site répond en HTTPS » ne mesure donc rien.

Ce qui distingue les deux états est le certificat PRÉSENTÉ. On ouvre la
connexion et on lit ce que le serveur envoie, ce qu'aucune lecture de
manifeste ne remplacerait : un Secret peut exister, être du bon type, et
n'être servi à personne parce que l'Ingress ne le déclare pas.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "vitrine"
HOTE = "vitrine.lab"
PORT_TLS = 30443
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
CERT_PAR_DEFAUT = "TRAEFIK DEFAULT CERT"

# Le contrôleur recharge sa configuration après notification : la bascule
# n'est pas immédiate. Budget borné, pour ne pas recaler un candidat dont la
# correction est juste.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _certificat_presente(host) -> str:
    """Ouvre la connexion TLS et rend le sujet du certificat servi.

    `-servername` envoie l'extension SNI : sans elle, le contrôleur ne sait
    pas quel hôte est demandé et sert son certificat par défaut, ce qui
    ferait échouer le test alors que le travail serait juste.
    """
    res = host.run(
        f"echo | openssl s_client -connect 127.0.0.1:{PORT_TLS} "
        f"-servername {HOTE} 2>/dev/null | openssl x509 -noout -subject -ext subjectAltName"
    )
    return res.stdout.strip()


# ----------------------------------------------------------------------
# 1. Le certificat est déposé là où le contrôleur sait le lire.
# ----------------------------------------------------------------------
def test_le_certificat_est_depose_dans_un_secret_du_bon_type(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable. Un Secret peut être parfait
    et n'être servi à personne, faute d'être déclaré dans l'Ingress."""
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get secret -o json")
    assert rc == 0, f"Impossible de lire les Secrets de {NAMESPACE}. {diagnostic}"

    tls = [
        s for s in json.loads(sortie).get("items", [])
        if s.get("type") == "kubernetes.io/tls"
    ]
    presents = {
        s["metadata"]["name"]: s.get("type") for s in json.loads(sortie).get("items", [])
    }
    assert tls, (
        f"Aucun Secret de type kubernetes.io/tls dans {NAMESPACE}. Les Secrets "
        f"présents sont {presents or 'aucun'}. Le TYPE compte : un Secret "
        "générique portant les mêmes clés ne serait pas lu par le contrôleur "
        "Ingress, qui sélectionne sur le type."
    )

    manquantes = [
        s["metadata"]["name"] for s in tls
        if not {"tls.crt", "tls.key"} <= set(s.get("data", {}))
    ]
    assert not manquantes, (
        f"Le ou les Secrets {manquantes} sont du bon type mais ne portent pas "
        "les deux clés attendues, tls.crt et tls.key. `kubectl create secret "
        "tls` les nomme correctement à votre place."
    )


# ----------------------------------------------------------------------
# 2. LE test : le serveur présente CE certificat, et le site répond toujours.
# ----------------------------------------------------------------------
def test_le_serveur_presente_le_certificat_de_l_hote_et_le_site_repond(host):
    """La preuve, prise sur la connexion elle-même.

    Les deux mesures sont dans le MÊME test, délibérément. « Le site répond en
    HTTPS » est déjà vrai AVANT le travail, puisque le contrôleur sert son
    certificat par défaut : isolée, cette assertion ferait un test vert qui ne
    mesure rien. Elle n'a de sens qu'accolée à celle qui distingue, où elle
    prend toute sa valeur : elle sépare une terminaison TLS réussie d'un site
    qu'on aurait cassé en la posant.

    Mesuré le 2026-09-16 : avant, `CN = TRAEFIK DEFAULT CERT` ; après,
    `CN = vitrine.lab`.
    """
    fin = time.monotonic() + BUDGET_S
    sujet = ""
    while time.monotonic() < fin:
        sujet = _certificat_presente(host)
        if sujet and CERT_PAR_DEFAUT not in sujet and HOTE in sujet:
            break
        time.sleep(PAS_S)

    assert sujet, (
        f"Aucune connexion TLS n'aboutit sur le port {PORT_TLS} du nœud. Le "
        "contrôleur Ingress répond-il encore ? "
        "`kubectl -n traefik get pods` le dira."
    )
    assert CERT_PAR_DEFAUT not in sujet, (
        f"Après {BUDGET_S} secondes, le serveur présente toujours son "
        f"certificat par défaut : « {sujet} ». Le contrôleur en fabrique un au "
        "démarrage et le sert à défaut d'autre chose, ce qui explique que le "
        "site réponde en HTTPS sans que rien n'ait été fait. Déclarer le "
        "Secret dans la section tls de l'Ingress est ce qui fait basculer le "
        "contrôleur sur le vôtre."
    )
    assert HOTE in sujet, (
        f"Le certificat servi ne nomme pas {HOTE} : « {sujet} ». Un client qui "
        "vérifie ne valide QUE le subjectAltName, le CN étant ignoré depuis "
        "des années : le certificat doit porter "
        f"`subjectAltName=DNS:{HOTE}`."
    )

    res = host.run(
        f"curl -sk -o /dev/null -w '%{{http_code}}' "
        f"--resolve {HOTE}:{PORT_TLS}:127.0.0.1 https://{HOTE}:{PORT_TLS}/ --max-time 10"
    )
    assert res.stdout.strip() == "200", (
        f"Le site ne répond plus : code HTTP « {res.stdout.strip() or 'aucun'} ». "
        "Le certificat est bien le vôtre, mais la route ne mène plus au "
        "service. Vérifiez que la règle d'hôte et le backend de l'Ingress "
        "n'ont pas été perdus en y ajoutant la section tls."
    )
