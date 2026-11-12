"""test_functional.py : cka-gateway-api-httproute

Six tests, un par état, qui lisent les conditions et exercent le routage réel,
jamais les commandes tapées.

Les deux derniers portent sur une panne posée par la préparation : la route
catalogue vise un Service d'un autre namespace sans ReferenceGrant. Le
contrôleur la refuse (ResolvedRefs=False, RefNotPermitted), et elle ne sert
rien. Déplacer le Service dans lab contournerait la panne : le test exige un
backend resté dans boutique.

Le premier test lit la condition `Programmed` de la Gateway plutôt que sa
seule existence. C'est la différence qui compte dans cette API : une Gateway
acceptée mais non programmée est un objet valide, visible dans `kubectl get`,
et qui ne route rien. Le cas se produit quand le port du listener ne
correspond à aucun point d'entrée du contrôleur.

Les deux applications répondent leur NOM, comme dans le lab Ingress jumeau :
le lab hérité servait nginx des deux côtés, donc ne pouvait pas distinguer un
routage inversé d'un routage correct.
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

# Le contrôleur programme la Gateway après notification. Budget borné, pour ne
# pas recaler un candidat dont la correction est juste.
BUDGET_S = 90
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


def _condition(objet: dict, type_: str) -> tuple[str, str]:
    """Rend (status, reason) d'une condition, ou ('', '') si elle manque."""
    for c in objet.get("status", {}).get("conditions", []):
        if c.get("type") == type_:
            return c.get("status", ""), c.get("reason", "")
    return "", ""


# ----------------------------------------------------------------------
# 1. La Gateway existe ET elle est programmée.
# ----------------------------------------------------------------------
def test_la_gateway_est_programmee(host):
    """Exister ne suffit pas, et c'est le piège propre à cette API.

    Une Gateway dont le listener déclare un port qui ne correspond à aucun
    point d'entrée du contrôleur est acceptée par l'API, apparaît dans
    `kubectl get`, et n'est jamais programmée. Rien ne route, et rien ne le
    dit sauf ses conditions.
    """
    def lire() -> dict:
        rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get gateway -o json")
        objets = json.loads(sortie).get("items", []) if rc == 0 and sortie else []
        return objets[0] if objets else {}

    gw = lire()
    fin = time.monotonic() + (BUDGET_S if gw else 0)
    while gw and _condition(gw, "Programmed")[0] != "True" and time.monotonic() < fin:
        time.sleep(PAS_S)
        gw = lire() or gw

    assert gw, message(
        en=f"No Gateway in namespace {NAMESPACE}. The CRDs and the "
        "GatewayClass are already installed by the cluster: the GatewayClass gives the name of the class "
        "to use.",
        fr=f"Aucune Gateway dans le namespace {NAMESPACE}. Les CRD et la "
        "GatewayClass sont déjà posées par le cluster : la GatewayClass donne le nom de la classe à "
        "employer.",
    )

    statut, raison = _condition(gw, "Programmed")
    accepte, raison_acc = _condition(gw, "Accepted")
    etat = (
        f"Programmed={statut or 'absent'} ({raison or 'sans raison'}), "
        f"Accepted={accepte or 'absent'} ({raison_acc or 'sans raison'})"
    )
    assert statut == "True", message(
        en=f"Gateway {gw['metadata']['name']} exists but is not "
        f"programmed: {etat}. An unprogrammed Gateway is a perfectly valid "
        "object that routes nothing. Check the class name, and the listener's "
        "PORT: it must match an entry point of the controller, otherwise "
        "nothing is listening.",
        fr=f"La Gateway {gw['metadata']['name']} existe mais n'est pas "
        f"programmée : {etat}. Une Gateway non programmée est un objet "
        "parfaitement valide qui ne route rien. Vérifiez le nom de la classe, "
        "et le PORT du listener : il doit correspondre à un point d'entrée du "
        "contrôleur, sans quoi rien ne l'écoute.",
    )


def _route(host) -> bool:
    """Une route vise-t-elle l'hôte ? Sans elle, rien n'est à attendre."""
    rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get httproute -o json")
    objets = json.loads(sortie).get("items", []) if rc == 0 and sortie else []
    return any(HOTE in (o.get("spec", {}).get("hostnames") or [HOTE]) for o in objets)


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
            en=f"No HTTPRoute targets {HOTE} in {NAMESPACE}.",
            fr=f"Aucune HTTPRoute ne vise {HOTE} dans {NAMESPACE}.",
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


# ----------------------------------------------------------------------
# La route catalogue, posée par la préparation, vise un Service d'un autre
# namespace sans autorisation. Le contrôleur la refuse : elle existe, elle est
# acceptée par la Gateway, et ses références ne sont pas résolues.
# ----------------------------------------------------------------------
ROUTE_CATALOGUE = "catalogue"
HOTE_CATALOGUE = "catalogue.local"
NAMESPACE_CATALOGUE = "boutique"


def _statut_catalogue(host) -> tuple[dict, dict]:
    """Rend (route, statut du parent entree), vides s'ils manquent."""
    rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get httproute {ROUTE_CATALOGUE} -o json")
    route = json.loads(sortie) if rc == 0 and sortie else {}
    parents = (route.get("status") or {}).get("parents") or []
    parent = next((p for p in parents if (p.get("parentRef") or {}).get("name") == "entree"), {})
    return route, parent


def _conditions(parent: dict) -> dict[str, tuple[str, str, int]]:
    return {c.get("type"): (c.get("status", ""), c.get("reason", ""), c.get("observedGeneration", -1))
            for c in parent.get("conditions") or []}


def _catalogue_resolue(route: dict, parent: dict) -> bool:
    cond = _conditions(parent)
    generation = (route.get("metadata") or {}).get("generation")
    return (
        cond.get("Accepted", ("",))[0] == "True"
        and cond.get("ResolvedRefs", ("",))[0] == "True"
        and all(c[2] == generation for c in cond.values())
    )


def test_la_route_catalogue_est_acceptee_et_resolue(host):
    route, parent = _statut_catalogue(host)
    fin = time.monotonic() + (BUDGET_S if parent else 0)
    while route and not _catalogue_resolue(route, parent) and time.monotonic() < fin:
        time.sleep(PAS_S)
        route, parent = _statut_catalogue(host)
    assert route, message(
        en=f"The HTTPRoute {ROUTE_CATALOGUE} no longer exists in {NAMESPACE}: it had to be repaired, not removed.",
        fr=f"La HTTPRoute {ROUTE_CATALOGUE} n'existe plus dans {NAMESPACE} : il fallait la réparer, pas la retirer.",
    )
    cibles = sorted({
        b.get("namespace", NAMESPACE)
        for r in route.get("spec", {}).get("rules") or [] for b in r.get("backendRefs") or []
    })
    cond = _conditions(parent)
    vu = {t: f"{s} ({r}, generation {g})" for t, (s, r, g) in cond.items()} or "no status for the Gateway entree"
    generation = route.get("metadata", {}).get("generation")
    assert _catalogue_resolue(route, parent) and cibles == [NAMESPACE_CATALOGUE], message(
        en=f"{ROUTE_CATALOGUE} (generation {generation}) sends to the namespace(s) {cibles} and reports: {vu}. "
        f"Expected Accepted=True and ResolvedRefs=True for the Gateway entree, up to date with the route's "
        f"generation, its backend still in {NAMESPACE_CATALOGUE}: the Service belongs to that team, which must "
        "allow the reference.",
        fr=f"{ROUTE_CATALOGUE} (génération {generation}) envoie vers le(s) namespace(s) {cibles} et déclare : {vu}. "
        f"Attendu Accepted=True et ResolvedRefs=True pour la Gateway entree, à jour de la génération de la "
        f"route, son backend toujours dans {NAMESPACE_CATALOGUE} : le Service appartient à cette équipe, qui doit "
        "autoriser la référence.",
    )


def test_catalogue_local_atteint_le_catalogue(host):
    res = host.run(
        f"curl -s --resolve {HOTE_CATALOGUE}:{PORT}:127.0.0.1 http://{HOTE_CATALOGUE}:{PORT}/ "
        "--max-time 8 -w '|%{http_code}'"
    )
    corps, _, code = res.stdout.rpartition("|")
    _, parent = _statut_catalogue(host)
    fin = time.monotonic() + (BUDGET_S if parent else 0)
    while corps.strip() != "catalogue" and time.monotonic() < fin:
        time.sleep(PAS_S)
        res = host.run(
            f"curl -s --resolve {HOTE_CATALOGUE}:{PORT}:127.0.0.1 http://{HOTE_CATALOGUE}:{PORT}/ "
            "--max-time 8 -w '|%{http_code}'"
        )
        corps, _, code = res.stdout.rpartition("|")
    assert corps.strip() == "catalogue", message(
        en=f"{HOTE_CATALOGUE} answers {corps.strip() or 'nothing'!r} (HTTP {code.strip() or 'none'}) instead of "
        "\"catalogue\". A route whose reference is refused sends nothing to its backend.",
        fr=f"{HOTE_CATALOGUE} répond {corps.strip() or 'rien'!r} (HTTP {code.strip() or 'aucun'}) au lieu de "
        "« catalogue ». Une route dont la référence est refusée n'envoie rien à son backend.",
    )
