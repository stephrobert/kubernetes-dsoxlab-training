"""test_functional.py : k8s-lire-un-node

Ces tests confrontent la fiche ~/lire-un-node/fiche.txt à ce que le Node
architecture-worker2 déclare au moment du test. Aucune valeur attendue n'est
écrite ici : elles viennent du cluster.

Les quatre valeurs demandées sont propres au nœud : son adresse interne, la
plage d'adresses de ses Pods et son Machine ID diffèrent de ceux des autres
nœuds, et toutes changent quand le cluster est recréé. Le runtime, le kubelet
et la capacité, eux, sont les mêmes sur les quatre nœuds kind et dans la
leçon : ils se recopiaient. Une valeur qui contient aussi celle d'un autre
nœud est refusée, pour qu'une liste recopiée en bloc ne passe pas.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/architecture.kubeconfig"
NOEUD = "architecture-worker2"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


@pytest.fixture(scope="module")
def noeud(host) -> dict:
    res = host.run(f"{ADMIN} get node {NOEUD} -o json")
    assert res.rc == 0, message(
        en=f"The Node {NOEUD} does not exist: the cluster is not the expected one.",
        fr=f"Le Node {NOEUD} n'existe pas : ce n'est pas le cluster attendu.",
    )
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


@pytest.fixture(scope="module")
def fiche(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/lire-un-node/fiche.txt")
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if ligne and not ligne.startswith("#") and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


def _valeur(fiche: dict[str, str], cle: str) -> str:
    valeur = fiche.get(cle, "")
    assert valeur, message(
        en=f"The key {cle!r} of ~/lire-un-node/fiche.txt has no value.",
        fr=f"La clé {cle!r} de ~/lire-un-node/fiche.txt n'a pas de valeur.",
    )
    return valeur


@pytest.fixture(scope="module")
def autres(host) -> list[dict]:
    """Les autres Nodes du cluster, pour refuser une valeur recopiée en bloc."""
    res = host.run(f"{ADMIN} get nodes -o json")
    assert res.rc == 0, message(
        en="Cannot list the Nodes of the cluster.",
        fr="Impossible de lister les Nodes du cluster.",
    )
    return [n for n in json.loads(res.stdout)["items"] if n["metadata"]["name"] != NOEUD]


def _adresse_interne(n: dict) -> str:
    for adresse in (n.get("status") or {}).get("addresses") or []:
        if adresse.get("type") == "InternalIP":
            return adresse.get("address", "")
    return ""


def _propre(valeur: str, attendue: str, autres_valeurs: list[str]) -> bool:
    """La valeur contient celle du nœud, et aucune de celles des autres nœuds."""
    mots = set(valeur.replace(",", " ").split())
    return attendue in mots and not any(a and a in mots for a in autres_valeurs)


# ----------------------------------------------------------------------
# 1. L'adresse interne du nœud.
# ----------------------------------------------------------------------
def test_l_adresse_interne_est_consignee(noeud, autres, fiche):
    attendue = _adresse_interne(noeud)
    valeur = _valeur(fiche, "adresse-interne")
    assert _propre(valeur, attendue, [_adresse_interne(n) for n in autres]), message(
        en=f"adresse-interne is {valeur!r}; expected the InternalIP of {NOEUD} alone "
           "(Addresses section of kubectl describe node).",
        fr=f"adresse-interne vaut {valeur!r} ; attendu l'InternalIP d'{NOEUD}, et elle seule "
           "(section Addresses de kubectl describe node).",
    )


# ----------------------------------------------------------------------
# 2. La plage d'adresses des Pods du nœud.
# ----------------------------------------------------------------------
def test_la_plage_des_pods_est_consignee(noeud, autres, fiche):
    attendue = (noeud.get("spec") or {}).get("podCIDR", "")
    valeur = _valeur(fiche, "plage-des-pods")
    assert _propre(valeur, attendue, [(n.get("spec") or {}).get("podCIDR", "") for n in autres]), message(
        en=f"plage-des-pods is {valeur!r}; expected the PodCIDR of {NOEUD} alone, "
           "written as kubectl describe node shows it.",
        fr=f"plage-des-pods vaut {valeur!r} ; attendu le PodCIDR d'{NOEUD}, et lui seul, "
           "écrit comme kubectl describe node l'affiche.",
    )


# ----------------------------------------------------------------------
# 3. Le Machine ID du nœud.
# ----------------------------------------------------------------------
def test_le_machine_id_est_consigne(noeud, autres, fiche):
    attendue = noeud["status"]["nodeInfo"].get("machineID", "")
    valeur = _valeur(fiche, "machine-id")
    assert _propre(valeur, attendue, [n["status"]["nodeInfo"].get("machineID", "") for n in autres]), message(
        en=f"machine-id is {valeur!r}; expected the Machine ID of {NOEUD} alone "
           "(System Info section of kubectl describe node).",
        fr=f"machine-id vaut {valeur!r} ; attendu le Machine ID d'{NOEUD}, et lui seul "
           "(section System Info de kubectl describe node).",
    )


# ----------------------------------------------------------------------
# 4. L'heure à laquelle le nœud est devenu Ready.
# ----------------------------------------------------------------------
MOIS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def test_l_heure_du_passage_a_ready_est_consignee(noeud, fiche):
    ready = next(c for c in noeud["status"]["conditions"] if c["type"] == "Ready")
    horodatage = ready["lastTransitionTime"]          # 2026-11-20T07:28:14Z
    jour, heure = horodatage.rstrip("Z").split("T")
    annee, mois, quantieme = jour.split("-")
    formes_du_jour = (jour, f"{int(quantieme)} {MOIS[int(mois) - 1]} {annee}",
                      f"{quantieme} {MOIS[int(mois) - 1]} {annee}")
    valeur = _valeur(fiche, "ready-depuis")
    assert heure in valeur and any(f in valeur for f in formes_du_jour), message(
        en=f"ready-depuis is {valeur!r}; expected the LastTransitionTime of the Ready "
           f"condition of {NOEUD}, date and time (Conditions section of kubectl describe node).",
        fr=f"ready-depuis vaut {valeur!r} ; attendu le LastTransitionTime de la condition "
           f"Ready d'{NOEUD}, date et heure (section Conditions de kubectl describe node).",
    )
