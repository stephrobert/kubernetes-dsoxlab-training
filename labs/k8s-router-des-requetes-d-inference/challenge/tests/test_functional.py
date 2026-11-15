"""test_functional.py : k8s-router-des-requetes-d-inference

Cinq tests, un par état demandé, dans l'ordre de l'énoncé. Ils lisent l'API du
cluster, puis envoient de vraies requêtes de complétion par la Gateway et
lisent QUI a répondu : le simulateur ajoute à chaque réponse l'en-tête
x-inference-pod, le nom du Pod qui l'a servie.

Le dernier test est la preuve du lab. Trois réplicas, dont un qui publie une
file d'attente de 40 requêtes et un cache KV plein : un Service ordinaire lui
enverrait un tiers du trafic, le pool d'inférence, guidé par ses métriques,
doit l'éviter. Le seuil de 10 % laisse passer un écart du sélecteur (une
métrique lue en retard au premier passage) sans laisser passer une répartition
aveugle, qui en donnerait 33 %.

La Gateway est jointe par l'adresse de cluster du Service qu'Istio crée pour
elle, depuis le control plane.
"""

from __future__ import annotations

import json
import time
import uuid

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "inference"
SELECTEUR = "selecteur"
PORT_MODELE = 8000
MODELE = "meta-llama/Llama-3.1-8B-Instruct"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
REQUETES = 30
PART_MAX_SATURE = 0.10

BUDGET_S = 120
PAS_S = 4


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str) -> dict:
    rc, sortie, _ = _kubectl(host, f"{args} -o json")
    if rc != 0 or not sortie:
        return {}
    return json.loads(sortie)


def _condition(conditions: list | None, type_: str) -> tuple[str, str]:
    for c in conditions or []:
        if c.get("type") == type_:
            return c.get("status", ""), c.get("reason", "")
    return "", ""


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _replicas(host) -> dict[str, str]:
    """Nom de chaque Pod du simulateur vers sa charge (libre ou saturee)."""
    pods = _json(host, f"-n {NAMESPACE} get pods -l app=modele").get("items", [])
    return {
        p["metadata"]["name"]: p["metadata"].get("labels", {}).get("charge", "")
        for p in pods
        if p.get("status", {}).get("phase") == "Running"
    }


def _pools(host) -> list[dict]:
    return _json(host, f"-n {NAMESPACE} get inferencepools.inference.networking.k8s.io").get("items", [])


def _gateway(host) -> dict:
    for gw in _json(host, f"-n {NAMESPACE} get gateways.gateway.networking.k8s.io").get("items", []):
        if gw.get("spec", {}).get("gatewayClassName") == "istio":
            return gw
    return {}


def _routes_vers_un_pool(host) -> list[dict]:
    routes = []
    for r in _json(host, f"-n {NAMESPACE} get httproutes.gateway.networking.k8s.io").get("items", []):
        for regle in r.get("spec", {}).get("rules") or []:
            for b in regle.get("backendRefs") or []:
                if b.get("group") == "inference.networking.k8s.io" and b.get("kind") == "InferencePool":
                    routes.append(r)
    return routes


def _adresse_gateway(host, gw: dict) -> str:
    nom = gw["metadata"]["name"]
    for selecteur in (f"gateway.networking.k8s.io/gateway-name={nom}", f"istio.io/gateway-name={nom}"):
        services = _json(host, f"-n {NAMESPACE} get svc -l {selecteur}").get("items", [])
        if services:
            return services[0].get("spec", {}).get("clusterIP", "")
    return ""


def _chemin_requis(host) -> str:
    """L'adresse de la Gateway, si une route y mène un pool ; sinon échec immédiat."""
    gw = _gateway(host)
    if not gw or not _routes_vers_un_pool(host):
        pytest.fail(message(
            en=f"No Gateway of class istio, or no HTTPRoute with an InferencePool backend, in {NAMESPACE}.",
            fr=f"Aucune Gateway de classe istio, ou aucune HTTPRoute dont le backend est un InferencePool, "
            f"dans {NAMESPACE}.",
        ))
    ip = _adresse_gateway(host, gw)
    if not ip:
        pytest.fail(message(
            en=f"No Service created by Istio for Gateway {gw['metadata']['name']}.",
            fr=f"Aucun Service créé par Istio pour la Gateway {gw['metadata']['name']}.",
        ))
    return ip


def _completion(host, ip: str) -> tuple[str, str]:
    """(code HTTP, Pod qui a répondu) pour une requête de complétion par la Gateway.

    Le prompt change à chaque requête : un prompt répété ferait jouer le cache
    de préfixe, qui renvoie volontairement vers le réplica qui l'a déjà vu.
    """
    corps = json.dumps({"model": MODELE, "prompt": f"Question {uuid.uuid4().hex}", "max_tokens": 8})
    res = host.run(
        f"curl -s -o /dev/null -D - --max-time 20 -H 'Content-Type: application/json' "
        f"-d '{corps}' http://{ip}/v1/completions"
    )
    code, pod = "", ""
    for ligne in res.stdout.replace("\r", "").splitlines():
        if ligne.startswith("HTTP/"):
            code = ligne.split()[1] if len(ligne.split()) > 1 else ""
        elif ligne.lower().startswith("x-inference-pod:"):
            pod = ligne.split(":", 1)[1].strip()
    return code, pod


# ----------------------------------------------------------------------
# 1. Le pool regroupe les trois réplicas et désigne le sélecteur, prêt.
# ----------------------------------------------------------------------
def test_le_pool_regroupe_les_trois_replicas(host):
    pools = _pools(host)
    assert pools, message(
        en=f"No InferencePool (inference.networking.k8s.io/v1) in {NAMESPACE}.",
        fr=f"Aucun InferencePool (inference.networking.k8s.io/v1) dans {NAMESPACE}.",
    )
    replicas = set(_replicas(host))
    pool = pools[0]
    spec = pool.get("spec", {})
    etiquettes = (spec.get("selector") or {}).get("matchLabels") or {}
    selecteur = ",".join(f"{k}={v}" for k, v in etiquettes.items())
    choisis = {
        p["metadata"]["name"]
        for p in (_json(host, f"-n {NAMESPACE} get pods -l {selecteur}").get("items", []) if selecteur else [])
    }
    assert choisis == replicas and len(replicas) == 3, message(
        en=f"The selector of pool {pool['metadata']['name']} ({selecteur or 'empty'}) picks "
        f"{sorted(choisis) or 'no Pod'}, the three replicas of the model are {sorted(replicas)}. The pool "
        "must see ALL replicas, the saturated one included: that is how it can avoid it.",
        fr=f"Le sélecteur du pool {pool['metadata']['name']} ({selecteur or 'vide'}) retient "
        f"{sorted(choisis) or 'aucun Pod'}, les trois réplicas du modèle sont {sorted(replicas)}. Le pool "
        "doit voir TOUS les réplicas, le saturé compris : c'est ainsi qu'il peut l'éviter.",
    )
    ports = [p.get("number") for p in spec.get("targetPorts") or []]
    assert PORT_MODELE in ports, message(
        en=f"targetPorts of the pool is {ports}: the simulator listens on {PORT_MODELE}.",
        fr=f"targetPorts du pool vaut {ports} : le simulateur écoute sur {PORT_MODELE}.",
    )
    ref = spec.get("endpointPickerRef") or {}
    assert ref.get("name") == SELECTEUR and (ref.get("port") or {}).get("number") == 9002, message(
        en=f"endpointPickerRef is {ref}: it must name the Service {SELECTEUR}, port 9002.",
        fr=f"endpointPickerRef vaut {ref} : il doit désigner le Service {SELECTEUR}, port 9002.",
    )

    def pret() -> int:
        return int(_json(host, f"-n {NAMESPACE} get deployment {SELECTEUR}").get("status", {}).get("readyReplicas") or 0)

    assert _attendre(pret, lambda n: n >= 1) >= 1, message(
        en=f"The endpoint picker {SELECTEUR} is still not ready: it is ready only once it has found its "
        f"pool. Its logs say which pool it waits for (kubectl logs -n {NAMESPACE} deploy/{SELECTEUR}): "
        "the name and the namespace must match.",
        fr=f"Le sélecteur d'endpoints {SELECTEUR} n'est toujours pas prêt : il ne l'est qu'une fois son pool "
        f"trouvé. Ses journaux disent quel pool il attend (kubectl logs -n {NAMESPACE} deploy/{SELECTEUR}) : "
        "le nom et le namespace doivent correspondre.",
    )


# ----------------------------------------------------------------------
# 2. La Gateway est programmée.
# ----------------------------------------------------------------------
def test_la_gateway_est_programmee(host):
    gw = _gateway(host)
    assert gw, message(
        en=f"No Gateway of class istio in {NAMESPACE}.",
        fr=f"Aucune Gateway de classe istio dans {NAMESPACE}.",
    )
    assert any(ln.get("protocol") == "HTTP" for ln in gw.get("spec", {}).get("listeners") or []), message(
        en=f"Gateway {gw['metadata']['name']} has no HTTP listener.",
        fr=f"La Gateway {gw['metadata']['name']} n'a aucun listener HTTP.",
    )
    gw = _attendre(
        lambda: _gateway(host) or gw,
        lambda g: _condition(g.get("status", {}).get("conditions"), "Programmed")[0] == "True",
    )
    programmee, raison = _condition(gw.get("status", {}).get("conditions"), "Programmed")
    assert programmee == "True", message(
        en=f"Gateway {gw['metadata']['name']} is not programmed: Programmed={programmee or 'absent'} "
        f"({raison or 'no reason'}). Without a load balancer, ask Istio for a ClusterIP Service with "
        "the annotation networking.istio.io/service-type.",
        fr=f"La Gateway {gw['metadata']['name']} n'est pas programmée : Programmed={programmee or 'absent'} "
        f"({raison or 'sans raison'}). Sans répartiteur de charge, demandez à Istio un Service ClusterIP "
        "par l'annotation networking.istio.io/service-type.",
    )


# ----------------------------------------------------------------------
# 3. Une route attachée à la Gateway mène au pool.
# ----------------------------------------------------------------------
def test_la_route_mene_au_pool(host):
    routes = _routes_vers_un_pool(host)
    assert routes, message(
        en=f"No HTTPRoute in {NAMESPACE} has a backendRef of group inference.networking.k8s.io, kind "
        "InferencePool. A backend of kind Service would spread requests blindly.",
        fr=f"Aucune HTTPRoute de {NAMESPACE} n'a de backendRef de groupe inference.networking.k8s.io, de "
        "kind InferencePool. Un backend de kind Service répartirait les requêtes à l'aveugle.",
    )

    def etat() -> tuple[str, str, str]:
        for r in _routes_vers_un_pool(host) or routes:
            for parent in r.get("status", {}).get("parents") or []:
                accepte = _condition(parent.get("conditions"), "Accepted")
                resolu = _condition(parent.get("conditions"), "ResolvedRefs")
                if accepte[0] == "True" and resolu[0] == "True":
                    return "True", "True", ""
                return accepte[0], resolu[0], f"{accepte[1]} / {resolu[1]}"
        return "", "", "aucun statut de parent"

    accepte, resolu, raisons = _attendre(etat, lambda e: e[0] == "True" and e[1] == "True")
    assert accepte == "True" and resolu == "True", message(
        en=f"The route to the pool is not Accepted and Resolved (Accepted={accepte or 'absent'}, "
        f"ResolvedRefs={resolu or 'absent'}: {raisons}). Do parentRefs name the Gateway, and does the "
        "backend name an existing InferencePool of the same namespace?",
        fr=f"La route vers le pool n'est pas Accepted et résolue (Accepted={accepte or 'absent'}, "
        f"ResolvedRefs={resolu or 'absent'} : {raisons}). parentRefs nomme-t-il la Gateway, et le backend "
        "un InferencePool existant du même namespace ?",
    )


# ----------------------------------------------------------------------
# 4. Des requêtes de complétion reçoivent la réponse des réplicas.
# ----------------------------------------------------------------------
def test_les_requetes_d_inference_aboutissent(host):
    ip = _chemin_requis(host)
    replicas = _replicas(host)
    resultats = _attendre(
        lambda: [_completion(host, ip) for _ in range(5)],
        lambda rs: all(code == "200" and pod in replicas for code, pod in rs),
        budget=90,
    )
    assert all(code == "200" and pod in replicas for code, pod in resultats), message(
        en=f"Requests to http://{ip}/v1/completions answer {resultats} (code, Pod). Expected: 200 and a "
        "replica of the model. 500 or 503: the Gateway does not reach the endpoint picker, or the "
        "picker has no endpoint. 404: no route matches the path.",
        fr=f"Les requêtes vers http://{ip}/v1/completions répondent {resultats} (code, Pod). Attendu : 200 "
        "et un réplica du modèle. 500 ou 503 : la Gateway n'atteint pas le sélecteur, ou le sélecteur "
        "n'a aucun endpoint. 404 : aucune route ne correspond au chemin.",
    )


# ----------------------------------------------------------------------
# 5. La répartition évite le réplica saturé.
# ----------------------------------------------------------------------
def test_la_repartition_evite_le_replica_sature(host):
    ip = _chemin_requis(host)
    replicas = _replicas(host)
    satures = {nom for nom, charge in replicas.items() if charge == "saturee"}
    assert satures, "Le réplica saturé du setup est introuvable : relancez dsoxlab run."

    resultats = [_completion(host, ip) for _ in range(REQUETES)]
    servis = [pod for code, pod in resultats if code == "200" and pod in replicas]
    compte = {nom: servis.count(nom) for nom in sorted(replicas)}
    vers_le_sature = sum(compte[n] for n in satures)

    assert len(servis) >= REQUETES * 0.9, message(
        en=f"Only {len(servis)} of {REQUETES} requests were answered by a replica: {compte}.",
        fr=f"Seules {len(servis)} requêtes sur {REQUETES} ont reçu la réponse d'un réplica : {compte}.",
    )
    assert vers_le_sature <= REQUETES * PART_MAX_SATURE, message(
        en=f"The saturated replica received {vers_le_sature} of {len(servis)} requests ({compte}). A blind "
        "spread gives it a third: the requests do not go through the endpoint picker. Is the route's "
        "backend the InferencePool, and does the pool name the picker?",
        fr=f"Le réplica saturé a reçu {vers_le_sature} requêtes sur {len(servis)} ({compte}). Une répartition "
        "aveugle lui en donne un tiers : les requêtes ne passent pas par le sélecteur d'endpoints. Le "
        "backend de la route est-il l'InferencePool, et le pool désigne-t-il le sélecteur ?",
    )
