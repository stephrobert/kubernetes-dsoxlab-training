"""Ce que l'apprenant lit ne porte ni emoji ni tiret cadratin.

La règle vient du style du blog, et elle est écrite dans `CONTRIBUTING.md` : pas
d'emoji, pas de tiret cadratin dans `scenario.md`, `README.md`, les indices et
les messages d'assertion. Elle ne tient que si quelque chose la vérifie : une
règle de rédaction sans contrôle dérive au premier lab écrit vite.

Le tiret cadratin mérite une explication, parce qu'il a l'air inoffensif. Il
arrive tout seul : un assistant en produit par habitude, un copier-coller depuis
une page anglaise en amène, et il se distingue mal d'un tiret ordinaire à la
relecture. Il n'appartient pas à la typographie de ce dépôt.

`conftest.py` fait exception, il est repris verbatim du catalogue Linux et le
faire diverger coûterait plus que le peu qu'il contient.

    pytest tests/test_style_apprenant.py -v
"""

from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"

#: Plages Unicode des emoji et des pictogrammes, plus le sélecteur de variante
#: qui les accompagne. Les flèches typographiques y sont : elles servent au même
#: usage décoratif et se rendent mal en terminal.
#:
#: Les bornes sont écrites en points de code, pas en caractères littéraux. Une
#: première version employait les échappements courts (`\\u2190-\\u21ff`) et
#: ruff les a convertis en caractères, dont le sélecteur de variante U+FE0F, qui
#: est INVISIBLE : la ligne devenait impossible à relire et une frappe malheureuse
#: l'aurait vidée sans que personne ne le voie.
PLAGES_EMOJI = [
    (0x1F300, 0x1FAFF),  # pictogrammes, symboles, transports, emoji récents
    (0x1F1E6, 0x1F1FF),  # drapeaux
    (0x2190, 0x21FF),  # flèches
    (0x2600, 0x27BF),  # symboles divers, dingbats
    (0x2B00, 0x2BFF),  # flèches et symboles supplémentaires
    (0xFE0F, 0xFE0F),  # sélecteur de variante emoji
]
EMOJI = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in PLAGES_EMOJI) + "]")

#: U+2014, le tiret cadratin.
CADRATIN = chr(0x2014)


def _textes_lus_par_l_apprenant() -> list[tuple[str, str]]:
    """Rend [(origine lisible, texte)] pour tout ce que l'apprenant lit."""
    textes: list[tuple[str, str]] = []

    # Les deux langues : le catalogue est bilingue, anglais prioritaire, et une
    # règle de style qui ne vaudrait que d'un côté ne vaudrait rien. Le tiret
    # cadratin, en particulier, arrive surtout par la traduction.
    for motif in ("*/scenario.md", "*/scenario.fr.md", "*/README.md", "*/README.fr.md"):
        for fichier in sorted(LABS.glob(motif)):
            textes.append((str(fichier.relative_to(RACINE)), fichier.read_text(encoding="utf-8")))

    # Les indices sont encodés : sans les décoder, le contrôle passerait au vert
    # sur du base64, qui ne contient évidemment ni emoji ni cadratin.
    for fichier in sorted(LABS.glob("*/challenge/hints.yaml")):
        document = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}
        for rang, indice in enumerate(document.get("hints") or [], start=1):
            for cle in ("text_fr", "text_en"):
                valeur = indice.get(cle)
                if not valeur:
                    continue
                try:
                    clair = base64.b64decode(str(valeur), validate=True).decode("utf-8")
                except (binascii.Error, ValueError, UnicodeDecodeError):
                    # Un indice illisible est le sujet de test_indices.py,
                    # qui le nomme et dit quoi faire. Ici on ne juge que le
                    # style de ce qui se décode.
                    continue
                textes.append(
                    (f"{fichier.relative_to(RACINE)} [indice {rang}, {cle}]", clair)
                )

    # Les messages d'assertion sont souvent le seul texte qu'un apprenant lit
    # avec attention : ils enseignent, donc ils suivent la même règle.
    for fichier in sorted(LABS.glob("*/challenge/tests/test_functional.py")):
        textes.append((str(fichier.relative_to(RACINE)), fichier.read_text(encoding="utf-8")))

    return textes


TEXTES = _textes_lus_par_l_apprenant()


def test_il_y_a_des_textes_a_lire() -> None:
    """Garde-fou : sans lui, un parcours cassé rendrait la suite verte à vide."""
    labs = list(LABS.glob("*/lab.yaml"))
    assert len(TEXTES) >= 5 * len(labs), (
        f"{len(TEXTES)} texte(s) pour {len(labs)} lab(s) : chaque lab a au moins "
        "un scenario et un README dans CHAQUE langue, plus ses indices. Le "
        "parcours est cassé, ou une traduction manque."
    )


@pytest.mark.parametrize("origine,texte", TEXTES, ids=[o for o, _ in TEXTES])
def test_pas_d_emoji(origine: str, texte: str) -> None:
    trouves = sorted(set(EMOJI.findall(texte)))

    assert not trouves, (
        f"{origine} porte {len(trouves)} emoji ou pictogramme : {trouves}.\n"
        "Le style du dépôt les exclut de ce que l'apprenant lit. Une consigne se "
        "dit avec des mots : un pictogramme se rend mal en terminal, se lit mal "
        "en synthèse vocale, et ne veut pas la même chose partout."
    )


@pytest.mark.parametrize("origine,texte", TEXTES, ids=[o for o, _ in TEXTES])
def test_pas_de_tiret_cadratin(origine: str, texte: str) -> None:
    occurrences = texte.count(CADRATIN)

    assert occurrences == 0, (
        f"{origine} porte {occurrences} tiret(s) cadratin (U+2014).\n"
        "Il n'appartient pas à la typographie du dépôt et arrive tout seul, par "
        "habitude de rédaction ou par copier-coller. Utilisez deux points, une "
        "virgule, ou une phrase de plus."
    )
