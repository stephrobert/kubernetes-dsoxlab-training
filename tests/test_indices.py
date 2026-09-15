"""Les indices sont encodés, bilingues, et vraiment traduits.

`challenge/hints.yaml` porte `text_fr` et `text_en` en **base64**, pour qu'un
apprenant n'y accède pas en ouvrant le fichier. Trois dérives sont possibles, et
aucune ne se voit à la lecture :

1. **Un indice en clair.** Il se lit d'un coup d'œil dans le dépôt, et le coût
   qui devait en payer le prix ne sert plus à rien.
2. **Une traduction qui n'en est pas une.** `text_fr` est une copie de l'anglais
   tant que personne n'est passé : le fichier a l'air complet, l'apprenant
   francophone reçoit de l'anglais.
3. **Des coûts incohérents.** Quatre indices du plus vague au plus explicite
   n'ont de sens que si leur coût croît : sinon l'apprenant paie le prix fort
   pour la piste la plus faible.

Le décodage sert aussi de contrôle de style : la règle du dépôt interdit emoji
et tiret cadratin dans ce que l'apprenant lit, et un indice est précisément cela.
Ce contrôle-là vit dans `test_style_apprenant.py`, qui décode les mêmes fichiers.

    pytest tests/test_indices.py -v
"""

from __future__ import annotations

import base64
import binascii
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
HINTS = sorted((RACINE / "labs").glob("*/challenge/hints.yaml"))


def _document(fichier: Path) -> dict:
    return yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}


def _decode(valeur: str) -> str:
    """Décode un champ base64, ou lève avec un message qui dit quoi faire."""
    # `validate=True` refuse les caractères hors alphabet base64 : sans lui, un
    # texte en clair composé de lettres se « décode » en octets aléatoires et le
    # contrôle passerait sur un indice lisible dans le dépôt.
    brut = base64.b64decode(valeur, validate=True)
    return brut.decode("utf-8")


def test_le_catalogue_a_des_indices() -> None:
    """Garde-fou : sans lui, un glob cassé rendrait la suite verte à vide."""
    labs = list((RACINE / "labs").glob("*/lab.yaml"))
    assert len(HINTS) == len(labs), (
        f"{len(HINTS)} fichier(s) d'indices pour {len(labs)} lab(s) : chaque lab "
        "doit porter challenge/hints.yaml."
    )


@pytest.mark.parametrize("fichier", HINTS, ids=lambda p: p.parent.parent.name)
def test_les_indices_sont_encodes_et_bilingues(fichier: Path) -> None:
    document = _document(fichier)
    indices = document.get("hints") or []

    assert indices, f"{fichier.relative_to(RACINE)} ne contient aucun indice."

    for rang, indice in enumerate(indices, start=1):
        for cle in ("text_fr", "text_en"):
            valeur = indice.get(cle)
            assert valeur, f"indice {rang} : {cle} est absent ou vide."
            try:
                _decode(str(valeur))
            except (binascii.Error, ValueError, UnicodeDecodeError) as erreur:
                pytest.fail(
                    f"{fichier.relative_to(RACINE)}, indice {rang}, {cle} : "
                    f"n'est pas du base64 UTF-8 ({erreur}).\n"
                    "Un indice en clair se lit en ouvrant le fichier, et le coût "
                    "qui devait en payer le prix ne sert plus à rien."
                )

        francais = _decode(str(indice["text_fr"]))
        anglais = _decode(str(indice["text_en"]))
        assert francais != anglais, (
            f"{fichier.relative_to(RACINE)}, indice {rang} : text_fr et text_en "
            "portent le même texte. La traduction n'a pas été faite : le fichier "
            "a l'air complet, et l'apprenant francophone reçoit de l'anglais."
        )


@pytest.mark.parametrize("fichier", HINTS, ids=lambda p: p.parent.parent.name)
def test_les_couts_croissent_et_tiennent_dans_le_bareme(fichier: Path) -> None:
    document = _document(fichier)
    indices = document.get("hints") or []
    couts = [int(indice.get("cost", 0)) for indice in indices]

    assert all(cout > 0 for cout in couts), (
        f"{fichier.relative_to(RACINE)} : un indice à coût nul est gratuit, donc "
        f"il n'a pas à être un indice (coûts : {couts})."
    )
    assert couts == sorted(couts), (
        f"{fichier.relative_to(RACINE)} : les coûts ne croissent pas ({couts}). "
        "Les indices vont du plus vague au plus explicite : l'apprenant qui "
        "s'arrête au premier doit payer le moins cher."
    )

    points = int(document.get("points", 100))
    assert sum(couts) < points, (
        f"{fichier.relative_to(RACINE)} : les indices coûtent {sum(couts)} pour "
        f"{points} points. Prendre tous les indices doit laisser une note, sinon "
        "le barème dit à l'apprenant que demander de l'aide revient à abandonner."
    )
