"""test_functional.py : k8s-appliquer-une-recommandation-vpa

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Un test vérifie
un seul état :

1. le VPA catalogue existe, vise le Deployment catalogue, en mode Off ;
2. il a produit une recommandation pour le conteneur catalogue ;
3. les requests du Deployment conviennent : le CPU entre lowerBound et
   upperBound, la mémoire entre la consommation mesurée et upperBound (la borne
   basse mémoire est le plancher de 250Mi du recommender, que la leçon dit de ne
   pas recopier) ;
4. les Pods en marche portent ces requests ;
5. le VPA n'a évincé aucun Pod.

Les cinq échouent sur l'état de départ : aucun VPA, une request CPU de 5m sous
la borne basse (25m au moins) et une request mémoire de 16Mi sous la
consommation du conteneur, qui garde une soixantaine de Mo. Le
cinquième n'a de sens qu'avec un VPA : sans lui, aucune éviction ne serait vraie
avant tout travail.

La recommandation se lit au moment du test : ses bornes bougent avec les
mesures, et c'est contre elles, pas contre une valeur figée, que les requests se
jugent.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "dimensionnement"
NOM = "catalogue"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE_RECOMMANDATION = 240
PAS = 10

_SUFFIXES = {"": 1, "k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12,
             "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "m": 10**-3}


def _quantite(valeur: str | None) -> float | None:
    """Une quantité Kubernetes (« 25m », « 262144k », « 250Mi », « 1 ») en unités de base."""
    if valeur is None:
        return None
    m = re.fullmatch(r"([0-9.]+)(m|k|M|G|T|Ki|Mi|Gi|Ti)?", str(valeur).strip())
    if not m:
        return None
    return float(m.group(1)) * _SUFFIXES[m.group(2) or ""]


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _vpa(host) -> dict:
    vpa = _json(host, f"-n {NS} get verticalpodautoscaler {NOM}")
    assert vpa is not None, message(
        en=f"No VerticalPodAutoscaler named {NOM} in {NS}.",
        fr=f"Aucun VerticalPodAutoscaler nommé {NOM} dans {NS}.",
    )
    return vpa


def _recommandation(host, attendre: bool) -> dict | None:
    """La recommandation du conteneur catalogue. Avec attendre, laisse au
    recommender le temps de la produire : il lit des mesures toutes les minutes."""
    fin = time.monotonic() + (ATTENTE_RECOMMANDATION if attendre else 0)
    while True:
        vpa = _vpa(host)
        for r in ((vpa.get("status") or {}).get("recommendation") or {}).get("containerRecommendations") or []:
            if r.get("containerName") == NOM and r.get("lowerBound") and r.get("upperBound"):
                return r
        if time.monotonic() >= fin:
            return None
        time.sleep(PAS)


def _en_mi(octets: float | None) -> str:
    return "?" if octets is None else f"{octets / 2**20:.0f}Mi"


def _consommation_memoire(host) -> float | None:
    """La plus forte consommation mémoire du conteneur catalogue parmi ses Pods,
    telle que metrics-server la mesure. Un Pod qui vient de démarrer n'a pas
    encore de mesure : on lui en laisse le temps."""
    for _ in range(12):
        res = host.run(f"{KUBECTL} get --raw /apis/metrics.k8s.io/v1beta1/namespaces/{NS}/pods")
        if res.rc == 0:
            mesures = [_quantite(c["usage"].get("memory"))
                       for p in json.loads(res.stdout).get("items", []) if p["metadata"]["name"].startswith(f"{NOM}-")
                       for c in p.get("containers", []) if c.get("name") == NOM]
            mesures = [m for m in mesures if m is not None]
            if mesures:
                return max(mesures)
        time.sleep(PAS)
    return None


def _requests_du_modele(host) -> dict:
    dep = _json(host, f"-n {NS} get deployment {NOM}")
    assert dep is not None, message(
        en=f"No Deployment {NOM} in {NS}: it is the application to size, it stays.",
        fr=f"Aucun Deployment {NOM} dans {NS} : c'est l'application à dimensionner, elle reste.",
    )
    conteneurs = dep["spec"]["template"]["spec"]["containers"]
    c = next((c for c in conteneurs if c["name"] == NOM), conteneurs[0])
    return (c.get("resources") or {}).get("requests") or {}


def _ecarts_aux_bornes(host, reco: dict, requests: dict) -> dict:
    """Ce qui, dans requests, sort des bornes de la recommandation."""
    ecarts = {}
    # Le CPU se juge entre les deux bornes.
    cpu = _quantite(requests.get("cpu"))
    bas, haut = _quantite(reco["lowerBound"].get("cpu")), _quantite(reco["upperBound"].get("cpu"))
    if cpu is None or bas is None or haut is None or not bas <= cpu <= haut:
        ecarts["cpu"] = (f"{requests.get('cpu')} hors de "
                         f"[{reco['lowerBound'].get('cpu')}, {reco['upperBound'].get('cpu')}]")
    # La mémoire, non : la borne basse du recommender est son plancher de
    # 250Mi, que la leçon dit de ne pas recopier. Elle se juge entre la
    # consommation que mesure metrics-server et la borne haute.
    memoire = _quantite(requests.get("memory"))
    haut = _quantite(reco["upperBound"].get("memory"))
    conso = _consommation_memoire(host)
    if memoire is None or haut is None or conso is None or not conso <= memoire <= haut:
        ecarts["memory"] = (f"{requests.get('memory')} hors de [{_en_mi(conso)} mesurés, "
                            f"{reco['upperBound'].get('memory')}]")
    return ecarts


# ----------------------------------------------------------------------
# 1. Le VPA existe, vise catalogue, en mode Off.
# ----------------------------------------------------------------------
def test_le_vpa_existe_en_mode_off(host):
    vpa = _vpa(host)
    cible = vpa["spec"].get("targetRef") or {}
    assert cible.get("kind") == "Deployment" and cible.get("name") == NOM, message(
        en=f"The VPA {NOM} targets {cible.get('kind')}/{cible.get('name')} instead of Deployment/{NOM}.",
        fr=f"Le VPA {NOM} vise {cible.get('kind')}/{cible.get('name')} au lieu de Deployment/{NOM}.",
    )
    mode = (vpa["spec"].get("updatePolicy") or {}).get("updateMode")
    assert mode == "Off", message(
        en=f"The VPA {NOM} is in mode {mode!r}: in any mode but Off it acts on the Pods by itself, "
        "where the instruction asks it only to recommend.",
        fr=f"Le VPA {NOM} est en mode {mode!r} : dans tout autre mode que Off, il agit seul sur les Pods, "
        "là où la consigne lui demande seulement de recommander.",
    )


# ----------------------------------------------------------------------
# 2. Le VPA a produit une recommandation.
# ----------------------------------------------------------------------
def test_le_vpa_a_produit_une_recommandation(host):
    reco = _recommandation(host, attendre=True)
    assert reco is not None, message(
        en=f"After {ATTENTE_RECOMMANDATION}s, the VPA {NOM} has produced no recommendation for the container "
        f"{NOM}. The recommender needs the Pods' metrics: metrics-server must answer, and the VPA must target "
        "the running Deployment.",
        fr=f"Après {ATTENTE_RECOMMANDATION}s, le VPA {NOM} n'a produit aucune recommandation pour le conteneur "
        f"{NOM}. Le recommender a besoin des mesures des Pods : metrics-server doit répondre, et le VPA viser "
        "le Deployment en marche.",
    )


# ----------------------------------------------------------------------
# 3. Les requests du Deployment sont entre lowerBound et upperBound.
# ----------------------------------------------------------------------
def test_les_requests_sont_dans_les_bornes(host):
    reco = _recommandation(host, attendre=True)
    assert reco is not None, message(
        en=f"The VPA {NOM} has no recommendation yet: the requests cannot be judged against it.",
        fr=f"Le VPA {NOM} n'a pas encore de recommandation : les requests ne se jugent pas sans elle.",
    )
    ecarts = _ecarts_aux_bornes(host, reco, _requests_du_modele(host))
    assert not ecarts, message(
        en=f"The requests of the Deployment {NOM} do not fit: {ecarts}. CPU goes between lowerBound and upperBound; "
        "memory between the usage metrics-server measures and upperBound.",
        fr=f"Les requests du Deployment {NOM} ne conviennent pas : {ecarts}. Le CPU se place entre lowerBound et "
        "upperBound ; la mémoire entre la consommation que mesure metrics-server et upperBound.",
    )


# ----------------------------------------------------------------------
# 4. Les Pods en marche portent ces requests.
# ----------------------------------------------------------------------
def test_les_pods_tournent_avec_ces_requests(host):
    voulues_brutes = _requests_du_modele(host)
    voulues = {k: _quantite(v) for k, v in voulues_brutes.items()}
    dep = _json(host, f"-n {NS} get deployment {NOM}")
    replicas = (dep or {}).get("spec", {}).get("replicas", 1)
    ecarts: dict[str, dict] = {}
    alignes = False
    for _ in range(18):
        pods = [p for p in (_json(host, f"-n {NS} get pods -l app={NOM}") or {}).get("items", [])
                if not p["metadata"].get("deletionTimestamp") and p["status"].get("phase") == "Running"
                and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])]
        ecarts = {}
        for p in pods:
            c = next((c for c in p["spec"]["containers"] if c["name"] == NOM), p["spec"]["containers"][0])
            portees = {k: _quantite(v) for k, v in ((c.get("resources") or {}).get("requests") or {}).items()}
            if portees != voulues:
                ecarts[p["metadata"]["name"]] = (c.get("resources") or {}).get("requests")
        if len(pods) == replicas and not ecarts:
            alignes = True
            break
        time.sleep(PAS)
    if alignes:
        # Porter les requests du Deployment ne suffit pas : au départ, les Pods
        # portent déjà celles du Deployment d'origine. Ces requests doivent
        # être celles que la recommandation justifie.
        reco = _recommandation(host, attendre=True)
        assert reco is not None, message(
            en=f"The VPA {NOM} has no recommendation yet: the Pods' requests cannot be judged against it.",
            fr=f"Le VPA {NOM} n'a pas encore de recommandation : les requests des Pods ne se jugent pas sans elle.",
        )
        hors = _ecarts_aux_bornes(host, reco, voulues_brutes)
        assert not hors, message(
            en=f"The running Pods of {NOM} carry requests that the recommendation does not justify: {hors}. "
            "Apply the recommendation in the Deployment, then let its Pods be recreated.",
            fr=f"Les Pods en marche de {NOM} portent des requests que la recommandation ne justifie pas : {hors}. "
            "Appliquez la recommandation dans le Deployment, puis laissez ses Pods être recréés.",
        )
        return
    raise AssertionError(message(
        en=f"The running Pods of {NOM} do not all carry the Deployment's requests ({len(pods)} ready out of "
        f"{replicas}, different: {ecarts}).",
        fr=f"Les Pods en marche de {NOM} ne portent pas tous les requests du Deployment ({len(pods)} prêts sur "
        f"{replicas}, différents : {ecarts}).",
    ))


# ----------------------------------------------------------------------
# 5. Le VPA n'a évincé aucun Pod.
# ----------------------------------------------------------------------
def test_le_vpa_n_a_evince_aucun_pod(host):
    _vpa(host)
    evenements = (_json(host, f"-n {NS} get events --field-selector reason=EvictedByVPA") or {}).get("items") or []
    victimes = sorted({e.get("involvedObject", {}).get("name", "?") for e in evenements})
    assert not victimes, message(
        en=f"The VPA evicted Pods of {NS}: {victimes}. In mode Off it only recommends; the decision to change "
        "the requests stays yours, in the Deployment.",
        fr=f"Le VPA a évincé des Pods de {NS} : {victimes}. En mode Off, il ne fait que recommander ; la "
        "décision de changer les requests vous revient, dans le Deployment.",
    )
