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
    fin = time.monotonic() + BUDGET_S
    gw = {}
    while time.monotonic() < fin:
        rc, sortie, _ = _kubectl(host, f"-n {NAMESPACE} get gateway -o json")
        objets = json.loads(sortie).get("items", []) if rc == 0 and sortie else []
        if objets:
            gw = objets[0]
            if _condition(gw, "Programmed")[0] == "True":
                break
        time.sleep(PAS_S)

    assert gw, message(
        en=f"No Gateway in namespace {NAMESPACE}. The CRDs and the "
        "GatewayClass are already installed by the cluster: `kubectl get "
        "gatewayclass` gives you the name of the class to use.",
        fr=f"Aucune Gateway dans le namespace {NAMESPACE}. Les CRD et la "
        "GatewayClass sont déjà posées par le cluster : `kubectl get "
        "gatewayclass` vous donne le nom de la classe à employer.",
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


# ----------------------------------------------------------------------
# 2. LE test : chaque chemin atteint SON application, et pas l'autre.
# ----------------------------------------------------------------------
def test_chaque_chemin_atteint_son_application(host):
    """La preuve, exercée sur les trois chemins.

    Le troisième est le contrôle : une route qui enverrait tout vers une seule
    application passerait les deux premières mesures sans router quoi que ce
    soit.

    Mesuré le 2026-09-16 : /api rend « api », /web rend « web », /autre rend
    404.
    """
    fin = time.monotonic() + BUDGET_S
    corps_api, code_api = "", ""
    while time.monotonic() < fin:
        corps_api, code_api = _demander(host, "/api")
        if corps_api == "api":
            break
        time.sleep(PAS_S)

    assert corps_api == "api", message(
        en=f"Path /api answers \"{corps_api or 'nothing'}\" (HTTP "
        f"{code_api or 'none'}) after {BUDGET_S} seconds, instead of \"api\". "
        "If the Gateway is indeed programmed, look at the route: `kubectl -n "
        "lab get httproute -o yaml` shows in its status whether it was "
        "ACCEPTED by the Gateway. A route whose parent is misnamed, or whose "
        "namespace is not allowed to attach, stays refused.",
        fr=f"Le chemin /api répond « {corps_api or 'rien'} » (HTTP "
        f"{code_api or 'aucun'}) après {BUDGET_S} secondes, au lieu de « api ». "
        "Si la Gateway est bien programmée, regardez la route : `kubectl -n "
        "lab get httproute -o yaml` montre dans son status si elle a été "
        "ACCEPTÉE par la Gateway. Une route dont le parent est mal nommé, ou "
        "dont le namespace n'est pas autorisé à s'attacher, reste refusée.",
    )

    corps_web, code_web = _demander(host, "/web")
    assert corps_web == "web", message(
        en=f"Path /web answers \"{corps_web or 'nothing'}\" (HTTP "
        f"{code_web or 'none'}) instead of \"web\", while /api is already "
        "correct. Only one of the two rules was written, or both point at the "
        "same service.",
        fr=f"Le chemin /web répond « {corps_web or 'rien'} » (HTTP "
        f"{code_web or 'aucun'}) au lieu de « web », alors que /api est déjà "
        "correct. Une seule des deux règles a été posée, ou les deux visent le "
        "même service.",
    )

    corps_autre, code_autre = _demander(host, "/autre")
    assert corps_autre not in ("api", "web"), message(
        en=f"A path you never declared, /autre, is served by "
        f"\"{corps_autre}\". So the routing sends everything to one application, "
        "and the two previous measurements proved nothing. A rule without "
        "`matches` accepts EVERYTHING arriving on the Gateway: each path "
        f"must carry its own. Code received: {code_autre}.",
        fr=f"Un chemin que vous n'avez pas déclaré, /autre, est servi par "
        f"« {corps_autre} ». Le routage envoie donc tout vers une application, "
        "et les deux mesures précédentes ne prouvaient rien. Une règle sans "
        "`matches` accepte TOUT ce qui arrive sur la Gateway : chaque chemin "
        f"doit porter le sien. Code obtenu : {code_autre}.",
    )
