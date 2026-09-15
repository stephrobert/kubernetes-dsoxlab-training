"""Toute collection Ansible employée doit être déclarée dans `requirements.yml`.

Le catalogue Linux jumeau a payé ce contrôle au prix fort : trois collections y
étaient utilisées, aucune déclarée. Deux se trouvaient installées par hasard sur
la machine de développement, la troisième non, et un capstone échouait sur un
« rc=4, Stats : {} », le code « unreachable » d'Ansible, qui envoie chercher un
problème de réseau pendant que la cause est une dépendance absente.

Le même piège guettait ici : `shared/kubeadm-cluster.yml` appelle
`community.general.modprobe`, et le premier lab est passé sans que rien ne dise
que cette collection était requise.

Le contrôle porte sur ce que les fichiers **emploient**, pas sur ce que la
machine a d'installé : une suite qui passe parce que la machine est bien garnie
ne dit rien de celle du prochain qui clone.

Périmètre : `labs/` **et** `shared/`. Le socle est la particularité de ce
dépôt : il n'appartient à aucun lab, il est inclus par tous, et l'oublier
reviendrait à ne contrôler que la moitié du catalogue.

    pytest tests/test_collections_declarees.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
REQUIREMENTS = RACINE / "requirements.yml"
SOURCES = ["labs", "shared"]

#: Un module en **position de clé** dans une tâche YAML :
#:
#:     - name: …
#:       community.general.modprobe:
#:
#: Chercher le motif n'importe où dans le texte ne marche pas : il remonterait
#: `net.ipv4.ip_forward`, `kubernetes.io/hostname` ou `lab.dsoxlab/cree-le`, qui
#: sont des sysctl, des labels et des annotations. Un garde-fou qui crie au loup
#: se fait désactiver, donc il ne regarde que là où un module peut se trouver.
QUALIFIE = re.compile(
    r"^\s*(?:-\s+)?([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)\.[a-z][a-z0-9_]*\s*:",
    re.MULTILINE,
)

#: Fournie avec ansible-core, jamais à déclarer.
INTEGREE = {"ansible.builtin"}


def _declarees() -> set[str]:
    if not REQUIREMENTS.is_file():
        pytest.fail(
            "requirements.yml est absent : les collections employées ne sont "
            "déclarées nulle part, et leur absence se manifestera par un rc=4 "
            "qui ressemble à un problème de réseau."
        )
    contenu = yaml.safe_load(REQUIREMENTS.read_text(encoding="utf-8")) or {}
    return {
        entree["name"] if isinstance(entree, dict) else str(entree)
        for entree in (contenu.get("collections") or [])
    }


def _playbooks() -> list[Path]:
    trouves: list[Path] = []
    for source in SOURCES:
        racine = RACINE / source
        if racine.is_dir():
            trouves += list(racine.rglob("*.yaml")) + list(racine.rglob("*.yml"))
    return sorted(trouves)


def _employees() -> dict[str, set[str]]:
    """Rend {collection: {fichiers qui l'emploient}}."""
    trouvees: dict[str, set[str]] = {}
    for fichier in _playbooks():
        texte = fichier.read_text(encoding="utf-8", errors="replace")
        for nom in QUALIFIE.findall(texte):
            if nom in INTEGREE:
                continue
            trouvees.setdefault(nom, set()).add(str(fichier.relative_to(RACINE)))
    return trouvees


def test_il_y_a_des_playbooks_a_lire() -> None:
    """Garde-fou : sans lui, un parcours cassé rendrait la suite verte à vide."""
    assert _playbooks(), (
        f"aucun YAML trouvé sous {SOURCES} : la découverte est cassée, pas le catalogue"
    )


def test_le_socle_est_dans_le_perimetre() -> None:
    """Le socle est inclus par tous les labs : l'oublier ne contrôlerait rien.

    Il porte aujourd'hui le seul appel à une collection externe du dépôt. Si ce
    fichier sortait du parcours, le test principal passerait au vert sans avoir
    rien regardé, ce qui est la panne du harnais déguisée en succès.
    """
    socle = RACINE / "shared" / "kubeadm-cluster.yml"
    assert socle.is_file(), "shared/kubeadm-cluster.yml est introuvable : le socle a bougé."
    assert socle in _playbooks(), "le socle n'est pas dans le parcours du contrôle."


def test_toute_collection_employee_est_declaree() -> None:
    employees = _employees()
    declarees = _declarees()
    manquantes = {nom: f for nom, f in employees.items() if nom not in declarees}

    if manquantes:
        detail = "\n".join(
            f"  {nom} : employée par {min(fichiers)}"
            + (f" et {len(fichiers) - 1} autre(s)" if len(fichiers) > 1 else "")
            for nom, fichiers in sorted(manquantes.items())
        )
        pytest.fail(
            "Ces collections sont employées mais absentes de requirements.yml :\n"
            f"{detail}\n"
            "Sur une machine qui ne les a pas, l'échec se présentera comme un "
            "rc=4 « unreachable », pas comme une dépendance manquante."
        )


def test_aucune_collection_declaree_inutile() -> None:
    """Une déclaration qui ne sert plus fait installer pour rien, et ment sur
    ce dont le catalogue a besoin."""
    employees = set(_employees())
    inutiles = sorted(nom for nom in _declarees() if nom not in employees)

    assert not inutiles, (
        f"Ces collections sont déclarées mais employées nulle part : {inutiles}.\n"
        "Soit un lab qui les utilisait a été retiré, soit la déclaration a été "
        "faite par précaution : dans les deux cas elle se retire."
    )
