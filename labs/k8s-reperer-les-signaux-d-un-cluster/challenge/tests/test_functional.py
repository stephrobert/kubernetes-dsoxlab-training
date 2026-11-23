"""test_functional.py : k8s-reperer-les-signaux-d-un-cluster

Deux alertes, lues là où elles vivent : dans l'API de Prometheus
(/api/v1/alerts), pas dans le ConfigMap. Une règle écrite mais jamais
rechargée, une règle à l'expression fausse ou un `for:` jamais atteint ne
donnent aucune alerte active, et c'est ce que l'équipe d'astreinte verrait.

Chaque test exige les deux côtés : l'alerte se déclenche sur le Pod en
souffrance, et ne se déclenche pas sur temoin-calme, qui a lui aussi des
limites mais ne les atteint jamais. Une expression trop large (toutes les
séries d'une métrique) se trahit par le témoin.

Aucun n'est vrai avant le travail : au départ, Prometheus n'a aucune règle.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

PROMETHEUS = "http://localhost:30090"
NAMESPACE = "signaux"

# Le ConfigMap met environ 70 secondes à atteindre le Pod Prometheus (mesuré le
# 2026-11-23), puis la règle doit tenir pendant son `for:`. Budget borné : le
# candidat qui vient d'écrire une règle juste n'est pas recalé pour autant.
BUDGET_S = 150
PAS_S = 10


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _alertes(host) -> list[dict]:
    res = host.run(f"curl -fsS {PROMETHEUS}/api/v1/alerts")
    if res.rc != 0:
        return []
    try:
        return json.loads(res.stdout)["data"]["alerts"]
    except (json.JSONDecodeError, KeyError):
        return []


def _actives(alertes: list[dict], nom: str) -> list[str]:
    """Les Pods de signaux pour lesquels l'alerte `nom` est déclenchée (firing)."""
    return sorted(
        a["labels"].get("pod", "")
        for a in alertes
        if a["labels"].get("alertname") == nom
        and a.get("state") == "firing"
        and a["labels"].get("namespace") == NAMESPACE
    )


def _regle_chargee(host, nom: str) -> bool:
    """Prometheus a-t-il chargé une règle d'alerte de ce nom ?"""
    res = host.run(f"curl -fsS {PROMETHEUS}/api/v1/rules?type=alert")
    if res.rc != 0:
        return False
    try:
        groupes = json.loads(res.stdout)["data"]["groups"]
    except (json.JSONDecodeError, KeyError):
        return False
    return any(r.get("name") == nom for g in groupes for r in g.get("rules", []))


def _verifier(host, nom: str, pod_vise: str, signal_en: str, signal_fr: str) -> None:
    # Sans règle chargée, l'attente ne servirait à rien : on la saute. Avec une
    # règle chargée, on laisse le temps à son for: de s'écouler.
    fin = time.monotonic() + (BUDGET_S if _regle_chargee(host, nom) else 0)
    pods: list[str] = []
    while True:
        alertes = _alertes(host)
        pods = _actives(alertes, nom)
        if any(p.startswith(pod_vise + "-") for p in pods) or time.monotonic() > fin:
            break
        time.sleep(PAS_S)

    assert alertes or host.run(f"curl -fsS {PROMETHEUS}/-/ready").rc == 0, message(
        en=f"Prometheus does not answer on {PROMETHEUS}. Its Pod lives in the "
        "supervision namespace.",
        fr=f"Prometheus ne répond pas sur {PROMETHEUS}. Son Pod vit dans le "
        "namespace supervision.",
    )
    assert any(p.startswith(pod_vise + "-") for p in pods), message(
        en=f"No firing alert named {nom} for the {pod_vise} Pod of {NAMESPACE} "
        f"after {BUDGET_S} seconds (firing for: {pods or 'no Pod'}). The alert must "
        f"detect {signal_en}. Check in {PROMETHEUS}/api/v1/rules that the rule is "
        "loaded and healthy: a ConfigMap takes about a minute to reach the Pod, "
        "then Prometheus must be reloaded, then the rule must hold for its for:.",
        fr=f"Aucune alerte {nom} déclenchée (firing) pour le Pod {pod_vise} de "
        f"{NAMESPACE} après {BUDGET_S} secondes (déclenchée pour : "
        f"{pods or 'aucun Pod'}). L'alerte doit repérer {signal_fr}. Vérifiez dans "
        f"{PROMETHEUS}/api/v1/rules que la règle est chargée et saine : un "
        "ConfigMap met environ une minute à atteindre le Pod, puis il faut "
        "recharger Prometheus, puis la règle doit tenir pendant son for:.",
    )
    temoins = [p for p in pods if p.startswith("temoin-calme-")]
    assert not temoins, message(
        en=f"The alert {nom} also fires for {temoins}. temoin-calme has limits too, "
        "but never reaches them: the expression is too wide.",
        fr=f"L'alerte {nom} se déclenche aussi pour {temoins}. temoin-calme a lui "
        "aussi des limites, mais ne les atteint jamais : l'expression est trop "
        "large.",
    )


def test_l_alerte_oomkilled_se_declenche_sur_memoire_courte(host):
    _verifier(
        host,
        "SignauxOOMKilled",
        "memoire-courte",
        "a container killed for lack of memory (OOMKilled) recently",
        "un conteneur tué par manque de mémoire (OOMKilled) récemment",
    )


def test_l_alerte_throttling_se_declenche_sur_calcul_serre(host):
    _verifier(
        host,
        "SignauxThrottling",
        "calcul-serre",
        "a container held back by its CPU limit (throttling)",
        "un conteneur bridé par sa limite CPU (throttling)",
    )
