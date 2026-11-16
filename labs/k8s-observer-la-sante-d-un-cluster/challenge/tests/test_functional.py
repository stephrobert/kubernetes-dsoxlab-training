"""test_functional.py : k8s-observer-la-sante-d-un-cluster

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. L'apprenant
rend kubectl top disponible (metrics-server, depuis le manifeste épinglé posé
dans ~/sante) puis écrit un bulletin de santé dans le ConfigMap bulletin du
namespace sante.

Aucune réponse n'est écrite ici : chaque test recalcule la vérité sur le
cluster au moment du check. Le Pod qui remplit sa mémoire est tiré au hasard par
le setup, et le nœud le plus réservé se calcule à partir des demandes de CPU de
tous les Pods. Rien n'est vrai avant le travail : metrics-server n'est pas
installé et le bulletin n'existe pas.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "sante"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, commande: str) -> dict:
    res = host.run(f"{KUBECTL} {commande} -o json")
    assert res.rc == 0, message(
        en=f"`kubectl {commande}` failed: {res.stderr.strip()}",
        fr=f"`kubectl {commande}` a échoué : {res.stderr.strip()}",
    )
    return json.loads(res.stdout)


def _bulletin(host) -> dict[str, str]:
    res = host.run(f"{KUBECTL} -n {NAMESPACE} get configmap bulletin -o json")
    assert res.rc == 0, message(
        en=f"No ConfigMap bulletin in namespace {NAMESPACE}. Write the health report there: keys "
        "pod-le-plus-gourmand and noeud-le-plus-reserve.",
        fr=f"Aucun ConfigMap bulletin dans le namespace {NAMESPACE}. Écrivez-y le bulletin de santé : clés "
        "pod-le-plus-gourmand et noeud-le-plus-reserve.",
    )
    return {k: v.strip() for k, v in (json.loads(res.stdout).get("data") or {}).items()}


def _milli(cpu: str) -> int:
    return int(cpu[:-1]) if cpu.endswith("m") else int(float(cpu) * 1000)


def _octets(memoire: str) -> int:
    unites = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "K": 1000, "M": 1000**2, "G": 1000**3}
    for suffixe, facteur in unites.items():
        if memoire.endswith(suffixe):
            return int(float(memoire[: -len(suffixe)]) * facteur)
    return int(memoire)


def _top_pods(host, delai: int = 90) -> dict[str, int]:
    """Mémoire de travail de chaque Pod du namespace, lue dans la Metrics API.

    metrics-server ne voit un Pod qu'après une ou deux collectes : on attend que
    les trois Pods aient une mesure, avec un budget borné.
    """
    fin = time.time() + delai
    mesures: dict[str, int] = {}
    while time.time() < fin:
        res = host.run(f"{KUBECTL} get --raw /apis/metrics.k8s.io/v1beta1/namespaces/{NAMESPACE}/pods")
        if res.rc == 0:
            mesures = {
                p["metadata"]["name"]: sum(_octets(c["usage"]["memory"]) for c in p["containers"])
                for p in json.loads(res.stdout).get("items", [])
            }
            if len(mesures) >= 3:
                return mesures
        time.sleep(5)
    return mesures


# ----------------------------------------------------------------------
# 1. kubectl top répond.
# ----------------------------------------------------------------------
def test_kubectl_top_repond(host):
    res = host.run(f"{KUBECTL} get apiservice v1beta1.metrics.k8s.io -o json")
    assert res.rc == 0, message(
        en="The Metrics API is not registered: metrics-server is not installed. Its manifest, pinned in "
        "version 0.9.0, is in ~/sante.",
        fr="La Metrics API n'est pas enregistrée : metrics-server n'est pas installé. Son manifeste, épinglé "
        "en version 0.9.0, est dans ~/sante.",
    )
    conditions = json.loads(res.stdout).get("status", {}).get("conditions") or []
    disponible = next((c for c in conditions if c.get("type") == "Available"), {})
    assert disponible.get("status") == "True", message(
        en=f"The Metrics API is registered but not available: {disponible.get('reason')} "
        f"{disponible.get('message')}. On kubeadm, the kubelets serve self-signed certificates: metrics-server "
        "refuses them without --kubelet-insecure-tls (lab only).",
        fr=f"La Metrics API est enregistrée mais pas disponible : {disponible.get('reason')} "
        f"{disponible.get('message')}. Sur kubeadm, les kubelets servent des certificats auto-signés : "
        "metrics-server les refuse sans --kubelet-insecure-tls (en lab seulement).",
    )
    fin = time.time() + 90
    while True:
        top = host.run(f"{KUBECTL} top nodes --no-headers")
        if top.rc == 0 or time.time() > fin:
            break
        time.sleep(5)
    assert top.rc == 0, message(
        en=f"`kubectl top nodes` still fails: {top.stderr.strip()}",
        fr=f"`kubectl top nodes` échoue encore : {top.stderr.strip()}",
    )


# ----------------------------------------------------------------------
# 2. Le bulletin nomme le Pod le plus gourmand en mémoire.
# ----------------------------------------------------------------------
def test_le_bulletin_nomme_le_pod_le_plus_gourmand(host):
    bulletin = _bulletin(host)
    mesures = _top_pods(host)
    assert mesures, message(
        en=f"The Metrics API gives no measure for the Pods of {NAMESPACE}: is metrics-server answering?",
        fr=f"La Metrics API ne donne aucune mesure pour les Pods de {NAMESPACE} : metrics-server répond-il ?",
    )
    gourmand = max(mesures, key=lambda nom: mesures[nom])
    assert bulletin.get("pod-le-plus-gourmand") == gourmand, message(
        en=f"The report names {bulletin.get('pod-le-plus-gourmand')!r} as the most memory-hungry Pod, but "
        f"`kubectl top pods -n {NAMESPACE}` gives {gourmand} (working set in bytes: {mesures}).",
        fr=f"Le bulletin nomme {bulletin.get('pod-le-plus-gourmand')!r} comme Pod le plus gourmand en mémoire, "
        f"mais `kubectl top pods -n {NAMESPACE}` donne {gourmand} (mémoire de travail en octets : {mesures}).",
    )


# ----------------------------------------------------------------------
# 3. Le bulletin nomme le nœud le plus réservé en CPU.
# ----------------------------------------------------------------------
def test_le_bulletin_nomme_le_noeud_le_plus_reserve(host):
    bulletin = _bulletin(host)
    noeuds = {n["metadata"]["name"]: _milli(n["status"]["allocatable"]["cpu"])
              for n in _json(host, "get nodes")["items"]}
    reserve = dict.fromkeys(noeuds, 0)
    for pod in _json(host, "get pods -A --field-selector=status.phase!=Succeeded,status.phase!=Failed")["items"]:
        noeud = pod["spec"].get("nodeName")
        if noeud in reserve:
            for c in pod["spec"]["containers"]:
                demande = ((c.get("resources") or {}).get("requests") or {}).get("cpu")
                if demande:
                    reserve[noeud] += _milli(demande)
    parts = {n: round(100 * reserve[n] / noeuds[n], 1) for n in noeuds}
    plus_reserve = max(parts, key=lambda n: parts[n])
    # describe node arrondit à l'entier : deux nœuds à moins d'un point d'écart
    # sont tous deux des réponses justes.
    acceptes = {n for n in parts if parts[plus_reserve] - parts[n] < 1}
    assert bulletin.get("noeud-le-plus-reserve") in acceptes, message(
        en=f"The report names {bulletin.get('noeud-le-plus-reserve')!r} as the node with the most reserved CPU, "
        f"but the CPU requests give {plus_reserve} (share of allocatable CPU: {parts} %). The Allocated "
        "resources section of `kubectl describe node` shows these requests, not the current usage.",
        fr=f"Le bulletin nomme {bulletin.get('noeud-le-plus-reserve')!r} comme nœud le plus réservé en CPU, mais "
        f"les demandes de CPU donnent {plus_reserve} (part du CPU allouable : {parts} %). La section Allocated "
        "resources de `kubectl describe node` montre ces demandes, pas la consommation du moment.",
    )
