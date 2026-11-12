"""test_functional.py : cka-gateway-api-httproute

Deux affirmations qui exercent le routage réel, jamais les commandes tapées.

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
