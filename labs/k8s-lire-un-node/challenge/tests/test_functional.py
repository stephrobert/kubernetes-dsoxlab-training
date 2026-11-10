"""test_functional.py : k8s-lire-un-node

Ces tests confrontent la fiche ~/lire-un-node/fiche.txt à ce que le Node
architecture-worker2 déclare au moment du test. Aucune valeur attendue n'est
écrite ici : runtime, versions et capacité viennent du cluster, ce qui laisse
le lab juste quand kind change de version ou quand l'hôte change de taille.

Un test vérifie un seul état demandé. Les formes équivalentes sont acceptées :
une version avec ou sans le « v », une mémoire en Ki, Mi ou Gi à 5 % près.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/architecture.kubeconfig"
NOEUD = "architecture-worker2"
UNITES = {"": 1, "k": 1000, "m": 1000**2, "g": 1000**3,
          "ki": 1024, "mi": 1024**2, "gi": 1024**3}
OUI = {"true", "ready", "oui", "yes", "vrai"}


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


def _octets(texte: str) -> float | None:
    """Une quantité mémoire Kubernetes ou humaine (« 4011484Ki », « 3.8 Gi »)."""
    m = re.fullmatch(r"\s*([0-9]+(?:[.,][0-9]+)?)\s*([kmg]i?)?b?\s*", texte.lower())
    if not m:
        return None
    return float(m.group(1).replace(",", ".")) * UNITES[m.group(2) or ""]


# ----------------------------------------------------------------------
# 1. Le runtime et sa version.
# ----------------------------------------------------------------------
def test_le_runtime_du_worker_est_consigne(noeud, fiche):
    runtime = noeud["status"]["nodeInfo"]["containerRuntimeVersion"]
    moteur, _, version = runtime.partition("://")
    valeur = _valeur(fiche, "runtime")
    assert moteur.lower() in valeur.lower() and version in valeur, message(
        en=f"runtime is {valeur!r}; it must name the runtime of {NOEUD} and its version.",
        fr=f"runtime vaut {valeur!r} ; il doit nommer le runtime d'{NOEUD} et sa version.",
    )


# ----------------------------------------------------------------------
# 2. La version du kubelet.
# ----------------------------------------------------------------------
def test_la_version_du_kubelet_est_consignee(noeud, fiche):
    attendue = noeud["status"]["nodeInfo"]["kubeletVersion"].lstrip("v")
    valeur = _valeur(fiche, "version-kubelet").strip().lstrip("vV")
    assert valeur == attendue, message(
        en=f"version-kubelet is {valeur!r}, which is not the kubelet version of {NOEUD}.",
        fr=f"version-kubelet vaut {valeur!r}, qui n'est pas la version du kubelet d'{NOEUD}.",
    )


# ----------------------------------------------------------------------
# 3. La capacité en CPU et en mémoire.
# ----------------------------------------------------------------------
def test_la_capacite_en_cpu_et_en_memoire_est_consignee(noeud, fiche):
    capacite = noeud["status"]["capacity"]
    cpu = _valeur(fiche, "cpu").strip()
    assert cpu == str(capacite["cpu"]), message(
        en=f"cpu is {cpu!r}, which is not the CPU capacity of {NOEUD}.",
        fr=f"cpu vaut {cpu!r}, qui n'est pas la capacité en CPU d'{NOEUD}.",
    )
    reelle = _octets(capacite["memory"])
    lue = _octets(_valeur(fiche, "memoire"))
    assert reelle and lue and abs(lue - reelle) <= 0.05 * reelle, message(
        en=f"memoire is {fiche.get('memoire')!r}, which is not the memory capacity of {NOEUD}, "
           "as shown under Capacity.",
        fr=f"memoire vaut {fiche.get('memoire')!r}, qui n'est pas la capacité mémoire d'{NOEUD}, "
           "telle qu'affichée sous Capacity.",
    )


# ----------------------------------------------------------------------
# 4. La condition Ready.
# ----------------------------------------------------------------------
def test_la_condition_ready_est_consignee(noeud, fiche):
    etat = next(
        (c["status"] for c in noeud["status"].get("conditions") or [] if c["type"] == "Ready"),
        "Unknown",
    )
    valeur = _valeur(fiche, "condition-ready").strip().lower()
    declare_pret = valeur in OUI
    assert declare_pret == (etat == "True") and (declare_pret or valeur in {"false", "unknown"}), message(
        en=f"condition-ready is {valeur!r}, which is not the status of the Ready condition of {NOEUD}.",
        fr=f"condition-ready vaut {valeur!r}, qui n'est pas le statut de la condition Ready d'{NOEUD}.",
    )
