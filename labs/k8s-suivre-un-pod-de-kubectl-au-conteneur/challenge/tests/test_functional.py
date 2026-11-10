"""test_functional.py : k8s-suivre-un-pod-de-kubectl-au-conteneur

Ces tests confrontent le relevé ~/suivre-un-pod/etapes.txt à l'état réel du
cluster. Un test vérifie un seul état demandé par l'énoncé.

L'attribution d'une étape est jugée sur le nom du composant, sans exiger une
forme au mot près : « default-scheduler » ou « kube-scheduler » valent pour le
placement, « kubelet » pour les étapes du conteneur. Une valeur qui nomme les
deux composants à la fois n'attribue rien et est refusée.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/architecture.kubeconfig"
NS = "suivre-un-pod"
IMAGE = "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str, absent: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/suivre-un-pod/etapes.txt")
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if ligne and not ligne.startswith("#") and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


def _valeur(releve: dict[str, str], cle: str) -> str:
    valeur = releve.get(cle, "")
    assert valeur, message(
        en=f"The key {cle!r} of ~/suivre-un-pod/etapes.txt has no value.",
        fr=f"La clé {cle!r} de ~/suivre-un-pod/etapes.txt n'a pas de valeur.",
    )
    return valeur


def _pods_de_suivi(host) -> list[dict]:
    return _json(host, f"-n {NS} get pods -l app=suivi", message(
        en="Cannot list the Pods of suivi.",
        fr="Impossible de lister les Pods de suivi.",
    )).get("items") or []


# ----------------------------------------------------------------------
# 1. Le Deployment suivi tourne.
# ----------------------------------------------------------------------
def test_le_deployment_suivi_a_un_replica_disponible(host):
    dep = _json(host, f"-n {NS} get deployment suivi", message(
        en=f"No Deployment suivi in the {NS} namespace.",
        fr=f"Aucun Deployment suivi dans le namespace {NS}.",
    ))
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    images = {c["image"] for c in dep["spec"]["template"]["spec"]["containers"]}
    assert disponibles == 1 and images == {IMAGE}, message(
        en=f"suivi has {disponibles} available replica(s) on {sorted(images)}; expected 1 on {IMAGE}.",
        fr=f"suivi a {disponibles} réplica(s) disponible(s) sur {sorted(images)} ; attendu 1 sur {IMAGE}.",
    )


# ----------------------------------------------------------------------
# 2. Le placement, attribué au scheduler.
# ----------------------------------------------------------------------
def test_l_etape_scheduled_est_attribuee_au_scheduler(releve):
    valeur = _valeur(releve, "scheduled").lower()
    assert "scheduler" in valeur and "kubelet" not in valeur, message(
        en=f"scheduled is {valeur!r}; the Scheduled step is performed by the scheduler.",
        fr=f"scheduled vaut {valeur!r} ; l'étape Scheduled n'est pas attribuée au bon composant.",
    )


# ----------------------------------------------------------------------
# 3. Les étapes du conteneur, attribuées au kubelet.
# ----------------------------------------------------------------------
def test_les_etapes_du_conteneur_sont_attribuees_au_kubelet(releve):
    fautives = [
        cle for cle in ("pulled", "created", "started")
        if "kubelet" not in _valeur(releve, cle).lower()
        or "scheduler" in _valeur(releve, cle).lower()
    ]
    assert not fautives, message(
        en=f"{', '.join(fautives)}: these steps are not attributed to the component "
           "that performed them, read the From column of the events.",
        fr=f"{', '.join(fautives)} : ces étapes ne sont pas attribuées au composant "
           "qui les a faites, lisez la colonne From des événements.",
    )


# ----------------------------------------------------------------------
# 4. Le kubelet qui agit est celui du Node du Pod.
# ----------------------------------------------------------------------
def test_le_kubelet_qui_agit_est_celui_du_node_du_pod(host, releve):
    noeuds = {p["spec"].get("nodeName") for p in _pods_de_suivi(host)} - {None}
    assert noeuds, message(
        en="No Pod of suivi is placed on a Node yet.",
        fr="Aucun Pod de suivi n'est encore placé sur un Node.",
    )
    valeur = _valeur(releve, "noeud-du-kubelet")
    assert valeur in noeuds, message(
        en=f"noeud-du-kubelet is {valeur!r}, which is not the Node running the Pod of suivi.",
        fr=f"noeud-du-kubelet vaut {valeur!r}, qui n'est pas le Node du Pod de suivi.",
    )
