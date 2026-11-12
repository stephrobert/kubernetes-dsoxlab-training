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

from conftest import lab_host, lab_target_host, message

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
    parfaitement valide, et ne pas dire quel contrôleur doit le servir."""
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get ingress -o json")
    assert rc == 0, message(
        en=f"Cannot read the Ingresses of {NAMESPACE}. {diagnostic}",
        fr=f"Impossible de lire les Ingress de {NAMESPACE}. {diagnostic}",
    )

    objets = json.loads(sortie).get("items", [])
    assert objets, message(
        en=f"No Ingress in namespace {NAMESPACE}. Both applications "
        "are already exposed, each by its own Service: what is missing is the "
        "rule saying which one serves which path.",
        fr=f"Aucun Ingress dans le namespace {NAMESPACE}. Les deux applications "
        "sont déjà exposées chacune par son Service : ce qui manque est la "
        "règle qui dit lequel sert quel chemin.",
    )

    pour_l_hote = [
        o for o in objets
        if any(r.get("host") == HOTE for r in o.get("spec", {}).get("rules", []))
    ]
    hotes = sorted({
        r.get("host") or "(aucun)"
        for o in objets for r in o.get("spec", {}).get("rules", [])
    })
    assert pour_l_hote, message(
        en=f"No rule targets host {HOTE}. The declared hosts are {hotes}. "
        "Without a host name, the rule applies to every request, which is not "
        "what you were asked for.",
        fr=f"Aucune règle ne vise l'hôte {HOTE}. Les hôtes déclarés sont {hotes}. "
        "Sans nom d'hôte, la règle vaut pour toute requête, ce qui n'est pas "
        "ce qui vous était demandé.",
    )

    sans_classe = [
        o["metadata"]["name"] for o in pour_l_hote
        if not o.get("spec", {}).get("ingressClassName")
        and "kubernetes.io/ingress.class" not in o["metadata"].get("annotations", {})
    ]
    assert not sans_classe, message(
        en=f"Ingress {sans_classe} names no class. Whether an Ingress "
        "without a class is served depends on each controller's settings; "
        "naming the class makes the choice explicit. The IngressClasses of "
        "the cluster name the one to use.",
        fr=f"L'Ingress {sans_classe} ne désigne aucune classe. Qu'un Ingress "
        "sans classe soit servi dépend des réglages de chaque contrôleur ; "
        "nommer la classe rend le choix explicite. Les IngressClass du "
        "cluster nomment celle à employer.",
    )


def _route(host) -> bool:
    """Une route vise-t-elle l'hôte ? Sans elle, rien n'est à attendre."""
    rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get ingress -o json")
    objets = json.loads(sortie).get("items", []) if rc == 0 and sortie else []
    return any(r.get("host") == HOTE for o in objets for r in o.get("spec", {}).get("rules", []))


def _attendre(host, chemin: str, attendu: str) -> tuple[str, str]:
    corps, code = _demander(host, chemin)
    fin = time.monotonic() + (BUDGET_S if _route(host) else 0)
    while corps != attendu and time.monotonic() < fin:
        time.sleep(PAS_S)
        corps, code = _demander(host, chemin)
    return corps, code


def _route_requise(host) -> None:
    if not _route(host):
        pytest.fail(message(
            en=f"No Ingress rule targets {HOTE} in {NAMESPACE}.",
            fr=f"Aucun Ingress ne vise {HOTE} dans {NAMESPACE}.",
        ))


# ----------------------------------------------------------------------
# Chaque chemin atteint SON application. Les deux applications répondent leur
# nom : un routage inversé se voit. Mesuré le 2026-09-16 : /api rend « api »,
# /web rend « web », /autre rend 404.
# ----------------------------------------------------------------------
def test_le_chemin_api_atteint_svc_api(host):
    _route_requise(host)
    corps, code = _attendre(host, "/api", "api")
    assert corps == "api", message(
        en=f"Path /api answers {corps or 'nothing'!r} (HTTP {code or 'none'}) instead of \"api\". If you read "
        "\"web\", the two services are swapped; a 404 means no rule takes that path.",
        fr=f"Le chemin /api répond {corps or 'rien'!r} (HTTP {code or 'aucun'}) au lieu de « api ». Si vous lisez "
        "« web », les deux services sont intervertis ; un 404 dit qu'aucune règle ne prend ce chemin.",
    )


def test_le_chemin_web_atteint_svc_web(host):
    _route_requise(host)
    corps, code = _attendre(host, "/web", "web")
    assert corps == "web", message(
        en=f"Path /web answers {corps or 'nothing'!r} (HTTP {code or 'none'}) instead of \"web\": its rule is "
        "missing, or points at the other service.",
        fr=f"Le chemin /web répond {corps or 'rien'!r} (HTTP {code or 'aucun'}) au lieu de « web » : sa règle "
        "manque, ou vise l'autre service.",
    )


def test_un_chemin_non_declare_n_atteint_aucune_application(host):
    """Le contrôle : une règle qui enverrait tout vers une seule application
    passerait les deux tests précédents sans router quoi que ce soit."""
    _route_requise(host)
    corps, code = _demander(host, "/autre")
    assert corps not in ("api", "web"), message(
        en=f"A path you never declared, /autre, is served by {corps!r} (HTTP {code}): the routing sends "
        "everything to one application. Each path must be declared on its own.",
        fr=f"Un chemin que vous n'avez pas déclaré, /autre, est servi par {corps!r} (HTTP {code}) : le routage "
        "envoie tout vers une application. Chaque chemin se déclare à part.",
    )
