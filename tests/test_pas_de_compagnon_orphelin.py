"""Aucun fichier de `challenge/` n'est là sans que rien ne l'appelle.

POURQUOI CE MODULE EXISTE.

Le convertisseur copie TOUS les fichiers du répertoire `solution/` d'un lab
hérité, et il a raison de le faire : un `solution.sh` hérité appelle souvent un
`solution.yaml` voisin par un chemin relatif, et n'en copier qu'un produit un
« path does not exist » à l'exécution.

Mais quand la solution est réécrite pour le catalogue, ce qui est la règle, le
compagnon reste. Plus rien ne l'appelle, personne ne le lit, et il continue de
vivre dans le dépôt.

Le 2026-09-16, deux de ces orphelins ont fait échouer la CI : `check-yaml`
refuse un fichier à plusieurs documents, et les deux `solution.yaml` hérités en
portaient. Le défaut n'était pas dans le YAML, il était dans sa présence.

Un lab fini ne porte que ce qu'il emploie. Un fichier que rien n'appelle est
une pièce morte que le prochain lecteur devra comprendre avant de découvrir
qu'elle ne sert à rien.

Ce module n'est pas collecté par la suite des labs : `testpaths` limite la
collecte aux challenges. Lancement :

    pytest tests/test_pas_de_compagnon_orphelin.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"

#: Ce que `challenge/` porte forcément, et que personne n'appelle par son nom :
#: le moteur les connaît.
ATTENDUS = {"solution.sh", "hints.yaml"}

CHALLENGES = sorted(d for d in LABS.glob("*/challenge") if d.is_dir())


def test_il_y_a_des_challenges_a_controler() -> None:
    """Garde-fou : un parcours cassé rendrait la suite verte à vide."""
    assert len(CHALLENGES) > 40, (
        f"Seulement {len(CHALLENGES)} challenge(s) trouvé(s) : le parcours est "
        "cassé, et le contrôle ne mesure plus rien."
    )


@pytest.mark.parametrize(
    "challenge", CHALLENGES, ids=lambda p: p.parent.name
)
def test_aucun_compagnon_n_est_orphelin(challenge: Path) -> None:
    solution = challenge / "solution.sh"
    appelants = solution.read_text(encoding="utf-8") if solution.is_file() else ""

    orphelins = []
    for fichier in sorted(challenge.iterdir()):
        if fichier.is_dir() or fichier.name in ATTENDUS:
            continue
        # Le compagnon est légitime si la solution le nomme, de n'importe
        # quelle façon : chemin relatif, absolu, ou simple nom de fichier.
        if fichier.name not in appelants:
            orphelins.append(fichier.name)

    assert not orphelins, (
        f"{challenge.relative_to(RACINE)} porte des fichiers que rien n'appelle :\n  "
        + "\n  ".join(orphelins)
        + "\n\nLe convertisseur copie tous les compagnons du lab hérité, et c'est "
        "voulu. Mais si la solution a été réécrite sans eux, ils ne servent plus : "
        "supprimez-les. Un lab fini ne porte que ce qu'il emploie."
    )
