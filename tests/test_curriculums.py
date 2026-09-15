"""Le dépôt ne cite jamais un poids de domaine qui contredit `curriculums.yml`.

POURQUOI CE MODULE EXISTE.

Le 2026-09-15, cinq issues du backlog ont vu les poids de *Cluster Setup* et
*System Hardening* échangés par une « correction » qui n'avait pas ouvert la
source, et qui affirmait pourtant l'avoir fait. Rien dans le dépôt n'aurait pu
le signaler : le chiffre vivait recopié dans chaque `lab.yaml`, chaque README
de lab et chaque issue, sans référence commune.

Un chiffre externe recopié dérive toujours. `curriculums.yml` le tient une
fois, avec sa source et sa date de vérification ; ce module refuse toute
mention du dépôt qui le contredit.

CE QUE CE MODULE NE FAIT PAS, et c'est délibéré : il ne va pas chercher le PDF
de la CNCF. Un test qui dépend du réseau échoue pour des raisons qui n'ont
rien à voir avec le dépôt, et il ne tournerait pas dans le hook pre-commit.
La confrontation à la source reste un geste humain, daté dans
`curriculums.yml`, et la procédure exacte est écrite en tête de ce fichier.

Ce module n'est pas collecté par la suite des labs : `testpaths` limite la
collecte aux challenges. Lancement :

    pytest tests/test_curriculums.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
from lecture_yaml import lire_yaml  # noqa: E402

CURRICULUMS = RACINE / "curriculums.yml"

#: Ce qu'on cherche : un nom de domaine suivi d'un pourcentage, dans les deux
#: langues et sous les formes qu'emploient réellement les labs. Le nom du
#: domaine peut porter des astérisques Markdown, d'où le `[*_]*`.
#:
#: Exemples attrapés :
#:   domaine *System Hardening* (10 % de l'épreuve)
#:   domain *Troubleshooting* (30 % of the exam)
#:   # Compétence du blueprint CKS, domaine System Hardening (10 %), citée...
#:
#: L'apostrophe typographique est écrite par son point de code : la voir en
#: clair dans une classe de caractères fait lever RUF001 à ruff, qui la
#: confond avec un accent grave. Elle doit pourtant y figurer, le français du
#: dépôt l'emploie.
CITATION = re.compile(
    r"(?:domaine|domain)\s+[*_]*(?P<domaine>[A-Z][A-Za-z,'\u2019\- ]+?)[*_]*\s*"
    r"\(\s*(?P<poids>\d+)\s*%",
)

#: Les fichiers où un poids peut être cité. On ne balaie pas le dépôt entier :
#: `todo/` n'est pas versionné et le journal de validation ne cite rien.
FICHIERS = sorted(
    [p for p in (RACINE / "labs").rglob("*.yaml") if p.name.startswith("lab")]
    + list((RACINE / "labs").rglob("README*.md"))
    + list((RACINE / "labs").rglob("scenario*.md"))
    + [RACINE / "README.md", RACINE / "README.fr.md"]
)


def _poids_officiels() -> dict[str, int]:
    """Tous les domaines connus, tous examens confondus, nom vers poids.

    Deux certifications peuvent nommer le même domaine : *Services and
    Networking* pèse 20 % au CKA comme au CKAD. Quand un nom est partagé avec
    des poids différents, on garde l'ensemble des poids admis, et le test
    accepte l'un d'eux : sans le contexte de la certification, on ne peut pas
    trancher, et refuser serait un faux positif.
    """
    donnees = lire_yaml(CURRICULUMS)
    admis: dict[str, set[int]] = {}
    for certification in (donnees.get("certifications") or {}).values():
        for domaine, poids in (certification.get("domaines") or {}).items():
            admis.setdefault(str(domaine), set()).add(int(poids))
    return admis


ADMIS = _poids_officiels()


def test_le_fichier_des_curriculums_est_complet() -> None:
    """Garde-fou : sans lui, un fichier vidé rendrait tous les autres verts."""
    donnees = lire_yaml(CURRICULUMS)
    assert donnees.get("source"), "curriculums.yml ne dit pas d'où viennent ses chiffres."
    assert donnees.get("verifie_le"), (
        "curriculums.yml ne dit pas QUAND ses chiffres ont été confrontés à la "
        "source. Sans date, personne ne sait s'ils sont encore vrais."
    )
    for nom, certification in (donnees.get("certifications") or {}).items():
        domaines = certification.get("domaines") or {}
        assert domaines, f"{nom} ne déclare aucun domaine."
        total = sum(int(p) for p in domaines.values())
        assert total == 100, (
            f"Les domaines de {nom} totalisent {total} %, pas 100. Un poids a "
            "été saisi de travers, ou un domaine manque."
        )


def test_les_fichiers_a_balayer_existent() -> None:
    """Sans ce contrôle, un chemin cassé rendrait la suite verte à vide."""
    assert len(FICHIERS) > 50, (
        f"Seulement {len(FICHIERS)} fichier(s) à balayer : le parcours est "
        "cassé, et le contrôle ne mesure plus rien."
    )


@pytest.mark.parametrize("fichier", FICHIERS, ids=lambda p: str(p.relative_to(RACINE)))
def test_aucun_poids_ne_contredit_le_curriculum(fichier: Path) -> None:
    ecarts = []
    for trouve in CITATION.finditer(fichier.read_text(encoding="utf-8")):
        domaine = trouve.group("domaine").strip()
        poids = int(trouve.group("poids"))
        attendus = ADMIS.get(domaine)
        if attendus is None:
            # Un domaine que le curriculum ne nomme pas : soit une coquille,
            # soit un domaine renommé par la CNCF. Les deux méritent un regard.
            ecarts.append(
                f"« {domaine} » n'est pas un domaine de curriculums.yml "
                f"(cité à {poids} %)"
            )
        elif poids not in attendus:
            ecarts.append(
                f"« {domaine} » est cité à {poids} %, le curriculum dit "
                f"{' ou '.join(f'{p} %' for p in sorted(attendus))}"
            )

    assert not ecarts, (
        f"{fichier.relative_to(RACINE)} contredit curriculums.yml :\n  "
        + "\n  ".join(ecarts)
        + "\n\nLe chiffre officiel vit dans curriculums.yml, avec sa source et "
        "sa date de vérification. Si c'est le curriculum qui a changé, c'est "
        "lui qu'on met à jour, après avoir ouvert le PDF de la CNCF, et pas "
        "l'inverse."
    )
