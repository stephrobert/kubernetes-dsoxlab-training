"""Vérifie que l'outillage du dépôt est cohérent avec lui-même.

Ce module existe à cause d'un incident réel, survenu dans un dépôt jumeau : au
cours d'une session de travail, un test de catalogue puis un hook de
`.pre-commit-config.yaml` ont disparu, sans qu'aucune opération git ne
l'explique. Plusieurs processus écrivent dans ces dépôts ; une édition
concurrente peut donc défaire une modification sans rien signaler.

Une disparition de ce genre est silencieuse par nature : un test absent ne
proteste pas, un hook absent ne se déclenche plus. Le seul remède est de rendre
l'incohérence détectable, ce que fait ce module :

1. tout hook local qui lance un test pointe vers un fichier qui existe ;
2. tout vérificateur de catalogue est soit câblé en pre-commit, soit
   explicitement recensé comme « à la demande », avec sa raison.

Le second point est le plus utile : un test présent mais débranché passe
totalement inaperçu, alors qu'il ne protège plus rien.

    pytest tests/test_outillage_coherent.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_TESTS = RACINE / "tests"
PRE_COMMIT = RACINE / ".pre-commit-config.yaml"

#: Vérificateurs délibérément NON câblés en pre-commit, avec la raison.
#: Les y mettre bloquerait un commit hors ligne ou ralentirait chaque commit.
#:
#: Rien n'y figure aujourd'hui : le contrôle des `doc_url` en ligne, qui est le
#: candidat naturel à cette liste, n'est pas un test de ce dépôt. Il est rendu
#: par le moteur, avec `dsoxlab validate-structure --check-urls`, et c'est la
#: CI qui le joue.
HORS_PRE_COMMIT: dict[str, str] = {}


def _hooks_locaux() -> list[dict]:
    configuration = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    hooks: list[dict] = []
    for depot in configuration.get("repos", []):
        if depot.get("repo") == "local":
            hooks.extend(depot.get("hooks", []))
    return hooks


HOOKS = _hooks_locaux()


def test_le_pre_commit_declare_des_hooks_locaux() -> None:
    """Garde-fou : un parsing cassé rendrait les tests suivants verts à vide."""
    assert HOOKS, "aucun hook local trouvé dans .pre-commit-config.yaml"


@pytest.mark.parametrize(
    "hook",
    [h for h in HOOKS if "pytest tests/" in str(h.get("entry", ""))],
    ids=lambda h: str(h.get("id", "?")),
)
def test_le_hook_pointe_un_test_existant(hook: dict) -> None:
    cible = re.search(r"pytest (tests/[\w.]+\.py)", str(hook["entry"]))
    assert cible, f"entry inattendue pour le hook {hook['id']} : {hook['entry']}"
    chemin = RACINE / cible.group(1)

    assert chemin.is_file(), (
        f"Le hook `{hook['id']}` lance {cible.group(1)}, qui n'existe pas.\n"
        "Soit le fichier a été supprimé et le hook doit suivre, soit il a disparu "
        "accidentellement et il faut le restaurer."
    )


@pytest.mark.parametrize(
    "fichier_de_test",
    sorted(p.name for p in DOSSIER_TESTS.glob("test_*.py")),
)
def test_le_verificateur_est_cable_ou_recense(fichier_de_test: str) -> None:
    """Un vérificateur présent mais débranché ne protège plus rien, en silence."""
    if fichier_de_test in HORS_PRE_COMMIT:
        pytest.skip(f"hors pre-commit assumé : {HORS_PRE_COMMIT[fichier_de_test]}")

    cable = any(fichier_de_test in str(hook.get("entry", "")) for hook in HOOKS)

    assert cable, (
        f"{fichier_de_test} existe dans tests/ mais aucun hook pre-commit ne le "
        "lance : il ne protège donc plus rien, sans que rien ne le signale.\n\n"
        "Soit ajoutez un hook local dans .pre-commit-config.yaml, soit inscrivez-le "
        "dans HORS_PRE_COMMIT (dans ce fichier) avec la raison de l'exclusion."
    )


def test_le_contrat_est_verifie_au_push() -> None:
    """`dsoxlab validate-structure` rend des contrôles qu'aucun test d'ici ne
    refait : liens relatifs cassés, fixtures déclarées, cohérence des cibles
    avec `meta.yml`. Le débrancher retirerait ces contrôles sans que la suite
    locale baisse d'un test, puisqu'elle ne les porte pas."""
    entrees = " ".join(str(hook.get("entry", "")) for hook in HOOKS)

    assert "validate-structure" in entrees, (
        "Aucun hook ne lance `dsoxlab validate-structure`. C'est le moteur qui "
        "vérifie le contrat déclaratif, les liens relatifs et les fixtures : "
        "aucun test de tests/ ne refait ce travail, et le retirer ouvrirait un "
        "trou qui ne se verrait nulle part."
    )
