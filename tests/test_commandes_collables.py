"""Une commande du cours se colle telle quelle, sous bash comme sous zsh.

Le 2026-11-19, en suivant le cours de `k8s-installer-kubectl`, Stéphane a collé
dans zsh :

    curl -fsSL https://dl.k8s.io/release/stable.txt; echo

et obtenu un 404, puis « Could not resolve host: echo ». zsh, par sa fonction
`url-quote-magic`, protège au collage les caractères spéciaux qui suivent une
URL non entourée de guillemets : le `;` est devenu `\\;`, collé à l'URL. La
commande était juste sous bash, fausse sous le shell par défaut de macOS et de
bien des postes.

D'où la règle : dans un bloc de commandes d'un cours ou d'un énoncé, une URL
hors guillemets ne porte ni n'est immédiatement suivie d'aucun caractère que
zsh protège (`;`, `&`, `|`, `?`, `*`, `(`, `)`, `<`, `>`, `[`, `]`). Une URL
qui en a besoin s'écrit entre guillemets, et une seconde commande va sur sa
propre ligne.

    pytest tests/test_commandes_collables.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"

#: Un bloc de commandes Markdown : ```bash ou ```sh, jusqu'à la clôture.
BLOC = re.compile(r"^```(?:bash|sh|shell|console)[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)

#: Une URL hors guillemets : précédée d'un blanc ou d'un début de ligne, jamais
#: d'un guillemet. Elle s'étend jusqu'au prochain blanc ou guillemet.
URL_NUE = re.compile(r"(?:^|(?<=[\s=]))https?://[^\s\"']+", re.MULTILINE)

#: Les caractères que `url-quote-magic` de zsh protège dans une URL collée.
PROTEGES = set(";&|?*()<>[]")

#: Un emplacement à remplacer, `<ip>`, `<port>` : l'apprenant l'édite avant de
#: lancer la commande, qui ne se colle donc pas telle quelle. Ce n'est pas le
#: piège visé, et le compter ferait un faux positif.
EMPLACEMENT = re.compile(r"<[a-z][a-z0-9_-]*>")


def fautes(commandes: str) -> list[str]:
    """Les URL d'un bloc de commandes qui casseraient au collage dans zsh."""
    return [
        url for url in URL_NUE.findall(commandes)
        if PROTEGES & set(EMPLACEMENT.sub("x", url))
    ]


def _documents() -> list[Path]:
    motifs = ("*/README.md", "*/README.fr.md", "*/challenge/README.md", "*/challenge/README.fr.md")
    return sorted(p for motif in motifs for p in LABS.glob(motif))


DOCUMENTS = _documents()


def test_le_controle_attrape_le_cas_qui_a_casse() -> None:
    """Garde-fou : un contrôle qui ne sait pas refuser ne contrôle rien."""
    assert fautes("curl -fsSL https://dl.k8s.io/release/stable.txt; echo\n")
    assert fautes("curl -fsSL https://exemple.test/api?page=2&taille=10\n")
    assert not fautes("curl -fsSL https://dl.k8s.io/release/stable.txt\necho\n")
    assert not fautes('curl -fsSL "https://exemple.test/api?page=2&taille=10"\n')
    assert not fautes('curl -fsSLO "${BASE}/kubectl"\n')
    # Un emplacement à remplacer n'est pas une faute ; ce qui le suit l'est.
    assert not fautes("curl -s http://<ip>/v1/completions | grep x\n")
    assert fautes("curl -s http://<ip>/v1/completions; echo\n")


def test_il_y_a_des_documents_a_lire() -> None:
    """Sans lui, un parcours cassé rendrait la suite verte à vide."""
    assert len(DOCUMENTS) >= 4 * len(list(LABS.glob("*/lab.yaml")))


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda p: str(p.relative_to(LABS)))
def test_aucune_url_ne_casse_au_collage(document: Path) -> None:
    texte = document.read_text(encoding="utf-8")
    trouvees = [url for bloc in BLOC.findall(texte) for url in fautes(bloc)]
    assert not trouvees, (
        f"{document.relative_to(RACINE)} : {len(trouvees)} URL casseraient au collage "
        f"dans zsh : {trouvees}.\nzsh protège les caractères spéciaux qui suivent une "
        "URL non entourée de guillemets (url-quote-magic) : un `;` collé devient `\\;`. "
        "Mettez l'URL entre guillemets, ou la commande suivante sur sa propre ligne."
    )
