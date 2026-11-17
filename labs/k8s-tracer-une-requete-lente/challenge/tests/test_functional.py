"""test_functional.py : k8s-tracer-une-requete-lente

Six tests, un par état demandé, dans l'ordre de l'énoncé. Ils lisent l'API du
cluster et l'API de requête de Jaeger, jamais un fichier de l'apprenant.

Comment Jaeger est lu : par le proxy de service de l'API server
(/api/v1/namespaces/observabilite/services/http:jaeger:16686/proxy/...), depuis
le control plane. Aucun Pod de lecture, aucun port-forward à arrêter.

Pourquoi les tests 4 et 5 envoient eux-mêmes des requêtes : une trace se
prouve par une requête faite PENDANT le test, dans une fenêtre de temps qui
commence avec lui. Des traces anciennes, laissées par une correction passée
puis défaite, ne valent rien.

Ce que vérifie le test 5, et que le 4 ne voit pas : sans propagation du
contexte par web, le waypoint écrit bien ses spans, mais chaque saut forme une
trace à part (mesuré le 2026-11-17 : 10 requêtes, 20 traces d'une span). Seule
une trace qui contient À LA FOIS une span de web et la span du saut vers le
service lent prouve que web fait suivre traceparent.

Le service lent est tiré au hasard par le setup. Le test le retrouve comme une
panne réelle se lit : dans les arguments du conteneur qui porte le délai.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

NAMESPACE = "boutique"
OBS = "observabilite"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
JAEGER = f"/api/v1/namespaces/{OBS}/services/http:jaeger:16686/proxy"
SERVICE_WAYPOINT = f"waypoint.{NAMESPACE}"
CANDIDATS = ("api", "stock")
DELAI = "--random-delay=true"

# Envoy exporte ses spans par lots (toutes les 5 s environ), le collecteur les
# regroupe à son tour : budget borné pour ne pas recaler une correction juste.
BUDGET_S = 60
PAS_S = 5
REQUETES = 3


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


def _maillage(host) -> dict:
    """La configuration du maillage (ConfigMap istio, clé mesh), en dict."""
    rc, sortie, _ = _kubectl(host, "-n istio-system get configmap istio -o jsonpath='{.data.mesh}'")
    if rc != 0 or not sortie:
        return {}
    return yaml.safe_load(sortie) or {}


def _fournisseur(host) -> str:
    """Le nom du fournisseur opentelemetry qui vise le collecteur, ou ''."""
    for p in _maillage(host).get("extensionProviders") or []:
        otel = p.get("opentelemetry") or {}
        if otel.get("service", "").startswith(f"otel-collector.{OBS}") and int(otel.get("port", 0)) == 4317:
            return p.get("name", "")
    return ""


def _fournisseur_requis(host) -> str:
    nom = _fournisseur(host)
    if not nom:
        pytest.fail(message(
            en="No opentelemetry provider aiming at otel-collector.observabilite, port 4317, in the "
            "mesh configuration: do this step first.",
            fr="Aucun fournisseur opentelemetry visant otel-collector.observabilite, port 4317, dans la "
            "configuration du maillage : faites d'abord cette étape.",
        ))
    return nom


def _waypoint(host) -> dict:
    """Le Gateway de classe istio-waypoint de boutique, ou {}."""
    for gw in _json(host, f"-n {NAMESPACE} get gateways.gateway.networking.k8s.io").get("items", []):
        if gw.get("spec", {}).get("gatewayClassName") == "istio-waypoint":
            return gw
    return {}


def _horloge(host) -> str:
    """L'heure du nœud moins 5 s, en RFC 3339 : début de la fenêtre du test."""
    return host.run("date -u -d '-5 sec' +%Y-%m-%dT%H:%M:%SZ").stdout.strip()


def _envoyer(host, n: int = REQUETES) -> list[str]:
    """n requêtes client -> web ; rend les lignes « code durée »."""
    lignes = []
    for _ in range(n):
        rc, sortie, _ = _kubectl(
            host,
            f"-n {NAMESPACE} exec client -- curl -s -o /dev/null -w '%{{http_code}} %{{time_total}}' "
            f"--max-time 10 -X POST -d bonjour http://web.{NAMESPACE}:9898/echo",
        )
        lignes.append(sortie if rc == 0 else f"échec ({rc})")
    return lignes


def _traces(host, debut: str) -> dict[str, list[dict]]:
    """Les traces du waypoint depuis `debut`, par identifiant : spans {svc, nom, ms}."""
    fin = host.run("date -u -d '+1 min' +%Y-%m-%dT%H:%M:%SZ").stdout.strip()
    rc, sortie, _ = _kubectl(
        host,
        f"get --raw '{JAEGER}/api/v3/traces?query.serviceName={SERVICE_WAYPOINT}"
        f"&query.startTimeMin={debut}&query.startTimeMax={fin}&query.searchDepth=50'",
    )
    if rc != 0 or not sortie:
        return {}
    traces: dict[str, list[dict]] = {}
    for rs in json.loads(sortie).get("result", {}).get("resourceSpans", []):
        attrs = {a["key"]: a.get("value", {}).get("stringValue", "") for a in rs.get("resource", {}).get("attributes", [])}
        for ss in rs.get("scopeSpans", []):
            for s in ss.get("spans", []):
                ms = (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e6
                traces.setdefault(s["traceId"], []).append(
                    {"svc": attrs.get("service.name", ""), "nom": s.get("name", ""), "ms": ms}
                )
    return traces


def _saut(nom: str, service: str) -> bool:
    """La span du waypoint est-elle celle du saut vers `service` ?"""
    return nom.startswith(f"{service}.{NAMESPACE}.svc.cluster.local:")


def _service_lent(host) -> str:
    """Le service dont le conteneur porte le délai, ou ''."""
    lents = []
    for svc in CANDIDATS:
        dep = _json(host, f"-n {NAMESPACE} get deployment {svc}")
        conteneurs = dep.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        args = " ".join((conteneurs[0].get("command") or []) + (conteneurs[0].get("args") or [])) if conteneurs else ""
        if DELAI in args:
            lents.append(svc)
    return lents[0] if len(lents) == 1 else ""


# ----------------------------------------------------------------------
# 1. Le maillage déclare un fournisseur de traces vers le collecteur.
# ----------------------------------------------------------------------
def test_le_maillage_declare_le_fournisseur_de_traces(host):
    """Un fournisseur se déclare dans meshConfig, que seul `istioctl install`
    réécrit : modifier la ConfigMap à la main serait défait au prochain install."""
    nom = _fournisseur(host)
    assert nom, message(
        en="The mesh configuration (ConfigMap istio in istio-system, key mesh) declares no "
        "extensionProviders entry of type opentelemetry with service "
        "otel-collector.observabilite.svc.cluster.local and port 4317. Copy /root/istio-ambient.yaml, "
        "add spec.meshConfig.extensionProviders, and apply it with istioctl install -y -f.",
        fr="La configuration du maillage (ConfigMap istio d'istio-system, clé mesh) ne déclare aucune "
        "entrée extensionProviders de type opentelemetry avec le service "
        "otel-collector.observabilite.svc.cluster.local et le port 4317. Copiez /root/istio-ambient.yaml, "
        "ajoutez spec.meshConfig.extensionProviders, et appliquez-le par istioctl install -y -f.",
    )


# ----------------------------------------------------------------------
# 2. Une Telemetry de niveau maillage trace 100 % des requêtes.
# ----------------------------------------------------------------------
def test_une_telemetry_trace_toutes_les_requetes(host):
    nom = _fournisseur_requis(host)
    trouvees = []
    for t in _json(host, "-n istio-system get telemetries.telemetry.istio.io").get("items", []):
        spec = t.get("spec", {})
        if spec.get("selector") or spec.get("targetRefs"):
            continue
        for tr in spec.get("tracing") or []:
            noms = [p.get("name") for p in tr.get("providers") or []]
            trouvees.append(f"{t['metadata']['name']} ({','.join(map(str, noms))}, "
                            f"{tr.get('randomSamplingPercentage', 'défaut')} %)")
            if nom in noms and float(tr.get("randomSamplingPercentage", 0)) == 100:
                return
    pytest.fail(message(
        en=f"No mesh-wide Telemetry in istio-system traces 100 % of requests with provider {nom}. "
        f"Found: {', '.join(trouvees) or 'none'}. Without randomSamplingPercentage: 100, Istio samples "
        "1 % of requests and the slow one may never be traced.",
        fr=f"Aucune Telemetry de niveau maillage dans istio-system ne trace 100 % des requêtes avec le "
        f"fournisseur {nom}. Trouvé : {', '.join(trouvees) or 'aucune'}. Sans randomSamplingPercentage: 100, "
        "Istio n'échantillonne qu'1 % des requêtes, et la lente peut ne jamais être tracée.",
    ))


# ----------------------------------------------------------------------
# 3. Un waypoint sert le namespace, et son Pod est prêt.
# ----------------------------------------------------------------------
def test_un_waypoint_sert_le_namespace(host):
    """ztunnel seul ne voit que des connexions : seul un waypoint (L7) écrit
    une span par requête HTTP."""
    gw = _waypoint(host)
    assert gw, message(
        en=f"No Gateway of class istio-waypoint in {NAMESPACE}: ztunnel alone works at L4 and writes no "
        "span. istioctl waypoint apply creates it.",
        fr=f"Aucun Gateway de classe istio-waypoint dans {NAMESPACE} : ztunnel seul travaille en L4 et "
        "n'écrit aucune span. istioctl waypoint apply le crée.",
    )
    nom = gw["metadata"]["name"]
    labels = _json(host, f"get namespace {NAMESPACE}").get("metadata", {}).get("labels", {})
    assert labels.get("istio.io/use-waypoint") == nom, message(
        en=f"The waypoint {nom} exists but the namespace does not use it: label istio.io/use-waypoint="
        f"{labels.get('istio.io/use-waypoint', 'absent')}. --enroll-namespace sets it.",
        fr=f"Le waypoint {nom} existe mais le namespace ne s'en sert pas : étiquette istio.io/use-waypoint="
        f"{labels.get('istio.io/use-waypoint', 'absente')}. --enroll-namespace la pose.",
    )
    gw = _attendre(
        lambda: _waypoint(host) or gw,
        lambda g: _condition(g.get("status", {}).get("conditions"), "Programmed")[0] == "True",
    )
    programme, raison = _condition(gw.get("status", {}).get("conditions"), "Programmed")
    assert programme == "True", message(
        en=f"The waypoint {nom} is not programmed: Programmed={programme or 'absent'} ({raison or 'no reason'}).",
        fr=f"Le waypoint {nom} n'est pas programmé : Programmed={programme or 'absent'} ({raison or 'sans raison'}).",
    )
    rc, _, diag = _kubectl(
        host,
        f"-n {NAMESPACE} wait --for=condition=Ready pod -l gateway.networking.k8s.io/gateway-name={nom} "
        "--timeout=60s",
    )
    assert rc == 0, message(
        en=f"The waypoint Pod is not Ready ({diag}). istioctl says « is ready! » before its Pod is: wait "
        "for the Pod itself.",
        fr=f"Le Pod du waypoint n'est pas Ready ({diag}). istioctl dit « is ready! » avant que son Pod le "
        "soit : attendez le Pod lui-même.",
    )


# ----------------------------------------------------------------------
# 4. Les spans du waypoint arrivent dans Jaeger.
# ----------------------------------------------------------------------
def test_les_spans_du_waypoint_arrivent_dans_jaeger(host):
    """Le piège du lab : tout est déclaré, le waypoint voit le trafic, et rien
    n'arrive. Chaque export échoue en « protocol error », sans un mot hors du
    journal debug, tant que le port du collecteur n'est pas reconnu comme gRPC."""
    _fournisseur_requis(host)
    debut = _horloge(host)
    reponses = _envoyer(host)
    traces = _attendre(lambda: _traces(host, debut), bool)
    _, services, _ = _kubectl(host, f"get --raw '{JAEGER}/api/v3/services'")
    assert traces, message(
        en=f"{REQUETES} requests sent ({'; '.join(reponses)}), and Jaeger received no span from "
        f"{SERVICE_WAYPOINT} within {BUDGET_S} s. Services known to Jaeger: {services or 'unreadable'}. "
        "If the waypoint sees the traffic, raise its tracing log level: istioctl proxy-config log "
        "deploy/waypoint -n boutique --level tracing:debug,grpc:debug, and read why the export fails.",
        fr=f"{REQUETES} requêtes envoyées ({'; '.join(reponses)}), et Jaeger n'a reçu aucune span de "
        f"{SERVICE_WAYPOINT} en {BUDGET_S} s. Services connus de Jaeger : {services or 'illisibles'}. "
        "Si le waypoint voit passer le trafic, montez son journal de traçage : istioctl proxy-config log "
        "deploy/waypoint -n boutique --level tracing:debug,grpc:debug, et lisez pourquoi l'export échoue.",
    )


# ----------------------------------------------------------------------
# 5. Une seule trace relie web au saut vers le service lent.
# ----------------------------------------------------------------------
def test_une_seule_trace_montre_le_service_lent(host):
    lent = _service_lent(host)
    if not lent:
        pytest.fail(message(
            en="Neither api nor stock carries the delay any more (or both do): the lab asks you to find "
            "the slow service, not to repair it. Run dsoxlab reset to start again.",
            fr="Ni api ni stock ne porte plus le délai (ou les deux le portent) : le lab demande de "
            "trouver le service lent, pas de le réparer. dsoxlab reset repart de zéro.",
        ))
    debut = _horloge(host)
    reponses = _envoyer(host)

    def complete(traces: dict) -> bool:
        return any(
            any(s["svc"] == "web" for s in spans)
            and any(s["svc"] == SERVICE_WAYPOINT and _saut(s["nom"], lent) for s in spans)
            for spans in traces.values()
        )

    traces = _attendre(lambda: _traces(host, debut), complete)
    resume = sorted({f"{len(sp)} span(s)" for sp in traces.values()})
    assert traces, message(
        en=f"No trace from the waypoint for the requests of this test ({'; '.join(reponses)}): the "
        "previous test says why.",
        fr=f"Aucune trace du waypoint pour les requêtes de ce test ({'; '.join(reponses)}) : le test "
        "précédent dit pourquoi.",
    )
    assert complete(traces), message(
        en=f"{len(traces)} trace(s) received ({', '.join(resume)}), but none holds both a span of the "
        f"service web and the waypoint span of the hop to the slow service. web does not forward the "
        "trace context: each hop is a separate trace. podinfo forwards it only with --otel-service-name.",
        fr=f"{len(traces)} trace(s) reçue(s) ({', '.join(resume)}), mais aucune ne contient à la fois une "
        f"span du service web et la span du waypoint pour le saut vers le service lent. web ne fait pas "
        "suivre le contexte de trace : chaque saut forme une trace à part. podinfo ne le fait suivre "
        "qu'avec --otel-service-name.",
    )


# ----------------------------------------------------------------------
# 6. Le diagnostic nomme le service lent.
# ----------------------------------------------------------------------
def test_le_diagnostic_nomme_le_service_lent(host):
    lent = _service_lent(host)
    if not lent:
        pytest.fail(message(
            en="Neither api nor stock carries the delay any more (or both do): diagnose, do not repair. "
            "Run dsoxlab reset to start again.",
            fr="Ni api ni stock ne porte plus le délai (ou les deux le portent) : diagnostiquez, ne "
            "réparez pas. dsoxlab reset repart de zéro.",
        ))
    cm = _json(host, f"-n {NAMESPACE} get configmap diagnostic")
    assert cm, message(
        en=f"No ConfigMap diagnostic in {NAMESPACE}. Write the slow service there, key service-lent.",
        fr=f"Aucune ConfigMap diagnostic dans {NAMESPACE}. Écrivez-y le service lent, clé service-lent.",
    )
    reponse = (cm.get("data", {}).get("service-lent") or "").strip().lower()
    assert reponse in CANDIDATS, message(
        en=f"The key service-lent holds {reponse!r}: expected api or stock.",
        fr=f"La clé service-lent contient {reponse!r} : attendu api ou stock.",
    )
    assert reponse == lent, message(
        en=f"The diagnostic names {reponse}, which is not the slow service. Read the trace again: which "
        "child span of web lasts more than a second?",
        fr=f"Le diagnostic nomme {reponse}, qui n'est pas le service lent. Relisez la trace : quelle "
        "span fille de web dure plus d'une seconde ?",
    )
