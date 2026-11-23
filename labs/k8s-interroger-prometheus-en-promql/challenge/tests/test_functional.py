"""test_functional.py : k8s-interroger-prometheus-en-promql

L'apprenant range quatre requêtes PromQL dans le ConfigMap requetes du
namespace atelier-promql. Chaque test évalue la requête de l'apprenant ET une
requête de référence AU MÊME INSTANT (paramètre time de l'API), puis compare
les deux résultats série par série : mêmes labels, mêmes valeurs.

Évaluer au même instant est ce qui rend la comparaison exacte. Deux requêtes
lancées à quelques secondes d'écart sur des compteurs vivants ne rendraient
jamais les mêmes nombres, et il faudrait une tolérance qui laisserait passer
des requêtes fausses.

Aucun test n'est vrai avant le travail : le ConfigMap n'existe pas.
"""

from __future__ import annotations

import json
import math
import shlex
import time

import pytest

from conftest import lab_host, lab_target_host, message

PROMETHEUS = "http://localhost:30090"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
NAMESPACE = "atelier-promql"

REFERENCES = {
    "memoire-par-namespace":
        'sum by (namespace) (container_memory_working_set_bytes{container!=""})',
    "top3-cpu-pods":
        'topk(3, sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!=""}[5m])))',
    "p95-duree-api":
        'histogram_quantile(0.95, sum by (handler, le) (rate(prometheus_http_request_duration_seconds_bucket[5m])))',
    "redemarrages-atelier":
        'increase(kube_pod_container_status_restarts_total{namespace="atelier-promql"}[10m])',
}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def requetes(host) -> dict:
    res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get configmap requetes -o json")
    if res.rc != 0:
        return {}
    return json.loads(res.stdout).get("data") or {}


@pytest.fixture(scope="module")
def instant() -> float:
    """Un instant légèrement passé, que les deux requêtes partagent."""
    return round(time.time() - 30, 3)


def _evaluer(host, requete: str, instant: float):
    """Rend (resultat, erreur). resultat : {labels triés: valeur}."""
    cmd = (
        f"curl -sS {PROMETHEUS}/api/v1/query --data-urlencode {shlex.quote('query=' + requete)} "
        f"--data-urlencode time={instant}"
    )
    res = host.run(cmd)
    try:
        corps = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None, f"réponse illisible de Prometheus : {res.stdout[:200]} {res.stderr[:200]}"
    if corps.get("status") != "success":
        return None, corps.get("error", "erreur inconnue")
    donnees = corps["data"]
    if donnees.get("resultType") != "vector":
        return None, f"type de résultat {donnees.get('resultType')}, un vecteur est attendu"
    resultat = {}
    for serie in donnees["result"]:
        labels = tuple(sorted((k, v) for k, v in serie["metric"].items() if k != "__name__"))
        resultat[labels] = float(serie["value"][1])
    return resultat, None


def _egaux(a: float, b: float) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def _comparer(host, requetes: dict, instant: float, cle: str, quoi_en: str, quoi_fr: str) -> None:
    assert requetes, message(
        en=f"No ConfigMap requetes in {NAMESPACE}, or it is empty. Store your four "
        "queries there, one per key.",
        fr=f"Pas de ConfigMap requetes dans {NAMESPACE}, ou il est vide. Rangez-y vos "
        "quatre requêtes, une par clé.",
    )
    requete = (requetes.get(cle) or "").strip()
    assert requete, message(
        en=f"The key {cle} is missing from the ConfigMap requetes. It must hold "
        f"the query that gives {quoi_en}.",
        fr=f"La clé {cle} manque dans le ConfigMap requetes. Elle doit porter la "
        f"requête qui donne {quoi_fr}.",
    )
    attendu, erreur = _evaluer(host, REFERENCES[cle], instant)
    assert erreur is None, message(
        en=f"The test could not evaluate its own reference query for {cle}: {erreur}. "
        "Is Prometheus running in the supervision namespace?",
        fr=f"Le test n'a pas pu évaluer sa propre requête de référence pour {cle} : "
        f"{erreur}. Prometheus tourne-t-il dans le namespace supervision ?",
    )
    obtenu, erreur = _evaluer(host, requete, instant)
    assert erreur is None, message(
        en=f"Prometheus refuses the query of {cle}: {erreur}",
        fr=f"Prometheus refuse la requête de {cle} : {erreur}",
    )

    def labels(cles) -> list[str]:
        return sorted(",".join(f"{k}={v}" for k, v in c) or "(aucun label)" for c in cles)

    assert set(obtenu) == set(attendu), message(
        en=f"The query of {cle} does not return the expected series. It returns "
        f"{len(obtenu)} series with the labels {labels(obtenu)[:5]}, "
        f"{len(attendu)} expected with the labels {labels(attendu)[:5]}. Check which "
        "labels the aggregation keeps and which series the selector filters.",
        fr=f"La requête de {cle} ne rend pas les séries attendues. Elle rend "
        f"{len(obtenu)} série(s) avec les labels {labels(obtenu)[:5]}, "
        f"{len(attendu)} attendue(s) avec les labels {labels(attendu)[:5]}. Vérifiez "
        "quels labels l'agrégation garde et quelles séries le sélecteur filtre.",
    )
    ecarts = [
        (",".join(f"{k}={v}" for k, v in c), obtenu[c], attendu[c])
        for c in attendu if not _egaux(obtenu[c], attendu[c])
    ]
    assert not ecarts, message(
        en=f"The query of {cle} returns the right series, but not the right values: "
        f"{ecarts[:3]} (series, yours, expected). Check the function and the "
        "time window.",
        fr=f"La requête de {cle} rend les bonnes séries, mais pas les bonnes "
        f"valeurs : {ecarts[:3]} (série, la vôtre, l'attendue). Vérifiez la "
        "fonction et la fenêtre de temps.",
    )


def test_memoire_par_namespace(host, requetes, instant):
    _comparer(host, requetes, instant, "memoire-par-namespace",
              "the memory in use per namespace", "la mémoire utilisée par namespace")


def test_top3_cpu_pods(host, requetes, instant):
    _comparer(host, requetes, instant, "top3-cpu-pods",
              "the three Pods that use the most CPU", "les trois Pods qui consomment le plus de CPU")


def test_p95_duree_api(host, requetes, instant):
    _comparer(host, requetes, instant, "p95-duree-api",
              "the P95 duration of Prometheus HTTP requests, per handler",
              "le P95 de la durée des requêtes HTTP de Prometheus, par handler")


def test_redemarrages_atelier(host, requetes, instant):
    _comparer(host, requetes, instant, "redemarrages-atelier",
              "the restarts of atelier-promql over the last 10 minutes",
              "les redémarrages d'atelier-promql sur les 10 dernières minutes")
