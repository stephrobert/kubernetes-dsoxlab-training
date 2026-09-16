"""test_functional.py : cka-ingress-path-routing

Deux affirmations qui exercent le routage réel, jamais les commandes tapées.

Les deux applications répondent leur NOM, et c'est délibéré. Le lab hérité
servait nginx des deux côtés : ses tests ne pouvaient donc pas distinguer un
routage correct d'un routage INVERSÉ, ni même vérifier qu'un routage existait.
Ici, `/api` doit répondre « api » et `/web` doit répondre « web ».

Le troisième chemin est le contrôle : un routage qui enverrait tout vers une
seule application passerait les deux premières mesures.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
HOTE = "app.local"
PORT = 30080
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Le contrôleur recharge sa configuration après notification : elle n'agit pas
# à la seconde où l'API accepte l'objet. Budget borné, pour ne pas recaler un
# candidat dont la correction est juste.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _demander(host, chemin: str) -> tuple[str, str]:
    """Rend (corps, code HTTP) pour une requête sur le chemin donné."""
    res = host.run(
        f"curl -s --resolve {HOTE}:{PORT}:127.0.0.1 "
        f"http://{HOTE}:{PORT}{chemin} --max-time 8 -w '|%{{http_code}}'"
    )
    corps, _, code = res.stdout.rpartition("|")
    return corps.strip(), code.strip()


# ----------------------------------------------------------------------
# 1. Une règle de routage existe pour cet hôte.
# ----------------------------------------------------------------------
def test_une_regle_de_routage_existe_pour_l_hote(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable. Un Ingress peut exister, être
    parfaitement valide, et n'être servi par aucun contrôleur faute de classe."""
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get ingress -o json")
    assert rc == 0, f"Impossible de lire les Ingress de {NAMESPACE}. {diagnostic}"

    objets = json.loads(sortie).get("items", [])
    assert objets, (
        f"Aucun Ingress dans le namespace {NAMESPACE}. Les deux applications "
        "sont déjà exposées chacune par son Service : ce qui manque est la "
        "règle qui dit lequel sert quel chemin."
    )

    pour_l_hote = [
        o for o in objets
        if any(r.get("host") == HOTE for r in o.get("spec", {}).get("rules", []))
    ]
    hotes = sorted({
        r.get("host") or "(aucun)"
        for o in objets for r in o.get("spec", {}).get("rules", [])
    })
    assert pour_l_hote, (
        f"Aucune règle ne vise l'hôte {HOTE}. Les hôtes déclarés sont {hotes}. "
        "Sans nom d'hôte, la règle vaut pour toute requête, ce qui n'est pas "
        "ce qui vous était demandé."
    )

    sans_classe = [
        o["metadata"]["name"] for o in pour_l_hote
        if not o.get("spec", {}).get("ingressClassName")
        and "kubernetes.io/ingress.class" not in o["metadata"].get("annotations", {})
    ]
    assert not sans_classe, (
        f"L'Ingress {sans_classe} ne désigne aucune classe. Un Ingress sans "
        "classe n'est servi par aucun contrôleur, sauf si une classe par "
        "défaut existe : `kubectl get ingressclass` dit celle du cluster."
    )


# ----------------------------------------------------------------------
# 2. LE test : chaque chemin atteint SON application, et pas l'autre.
# ----------------------------------------------------------------------
def test_chaque_chemin_atteint_son_application(host):
    """La preuve, exercée sur les trois chemins.

    Les deux applications répondent leur nom : un routage inversé serait donc
    détecté, là où deux backends identiques l'auraient laissé passer.

    Le troisième chemin est le contrôle. Une règle qui enverrait tout vers une
    seule application passerait les deux premières mesures sans router quoi que
    ce soit.

    Mesuré le 2026-09-16 : /api rend « api », /web rend « web », et /autre rend
    404.
    """
    fin = time.monotonic() + BUDGET_S
    corps_api, code_api = "", ""
    while time.monotonic() < fin:
        corps_api, code_api = _demander(host, "/api")
        if corps_api == "api":
            break
        time.sleep(PAS_S)

    assert corps_api == "api", (
        f"Le chemin /api répond « {corps_api or 'rien'} » (HTTP "
        f"{code_api or 'aucun'}) après {BUDGET_S} secondes, au lieu de « api ». "
        "L'application qui doit le servir répond son propre nom : si vous "
        "lisez « web », les deux services sont intervertis ; si vous lisez un "
        "404, aucune règle ne prend ce chemin."
    )

    corps_web, code_web = _demander(host, "/web")
    assert corps_web == "web", (
        f"Le chemin /web répond « {corps_web or 'rien'} » (HTTP "
        f"{code_web or 'aucun'}) au lieu de « web », alors que /api est déjà "
        "correct. Une seule des deux règles a été posée, ou les deux visent le "
        "même service."
    )

    corps_autre, code_autre = _demander(host, "/autre")
    assert corps_autre not in ("api", "web"), (
        f"Un chemin que vous n'avez pas déclaré, /autre, est servi par "
        f"« {corps_autre} ». Le routage envoie donc tout vers une application, "
        "et les deux mesures précédentes ne prouvaient rien : elles auraient "
        "été vertes avec une règle qui ne route pas. Vérifiez que vos chemins "
        f"sont bien déclarés séparément. Code obtenu : {code_autre}."
    )
