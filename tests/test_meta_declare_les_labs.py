"""Tout lab livré est déclaré dans `meta.yml`, et réciproquement.

POURQUOI CE MODULE EXISTE.

Le 2026-09-16, deux labs CKS validés, `cks-rbac-least-privilege` et
`cks-audit-log-policy`, se sont retrouvés absents de `meta.yml` après une
manipulation de branches. Conséquence : ils apparaissaient dans la table de
couverture du README, qui se construit à partir des `labs/*/lab.yaml`, mais
pas dans le parcours recommandé, qui se construit à partir de `meta.yml`. Un
apprenant qui suit le parcours ne les aurait jamais joués.

Rien ne pouvait le signaler. `dsoxlab validate-structure` lit les répertoires
de `labs/` et ne sait rien de `meta.yml` ; `check-labs-completude.py` fait de
même ; `gen_catalog.py` rend les deux vues sans se plaindre qu'elles
divergent. Chacun avait raison de son côté, et le trou était entre les deux.

Le contrôle porte donc sur l'ÉCART entre deux sources, dans les deux sens :

- un lab sur disque mais non déclaré est invisible du parcours ;
- un lab déclaré mais absent du disque casse le parcours, et `gen_catalog.py`
  le rend avec la mention « déclaré, absent du catalogue », ce qui vaut mieux
  qu'un silence mais reste un défaut.

Ce module n'est pas collecté par la suite des labs : `testpaths` limite la
collecte aux challenges. Lancement :

    pytest tests/test_meta_declare_les_labs.py -v
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
from lecture_yaml import lire_yaml  # noqa: E402

META = RACINE / "meta.yml"
LABS = RACINE / "labs"


def _declares() -> list[str]:
    """Les labs que `meta.yml` déclare, dans l'ordre, section par section."""
    donnees = lire_yaml(META)
    declares: list[str] = []
    for section in donnees.get("sections") or []:
        declares += [str(lab) for lab in (section.get("labs") or [])]
    return declares


def _sur_disque() -> set[str]:
    """Les labs réellement livrés : un répertoire qui porte un `lab.yaml`."""
    return {d.name for d in LABS.iterdir() if (d / "lab.yaml").is_file()}


def test_le_parcours_n_est_pas_vide() -> None:
    """Garde-fou : un `meta.yml` aux sections vides rendrait tout le reste vert.

    C'est l'état dans lequel le dépôt a vécu jusqu'au 2026-09-15, et personne
    ne l'a vu : les trois sections déclaraient `labs: []`, l'affichage
    retombait sur un tri alphabétique, et rien ne s'en plaignait.
    """
    declares = _declares()
    assert len(declares) > 30, (
        f"Seulement {len(declares)} lab(s) déclaré(s) dans meta.yml : les "
        "sections sont vides ou le parcours est cassé, et l'apprenant se "
        "retrouve devant un catalogue sans ordre."
    )


def test_chaque_lab_livre_est_declare_dans_le_parcours() -> None:
    oublies = sorted(_sur_disque() - set(_declares()))
    assert not oublies, (
        "Lab(s) livré(s) mais absent(s) du parcours de meta.yml :\n  "
        + "\n  ".join(oublies)
        + "\n\nIls apparaissent dans la table de couverture du README, qui se "
        "construit depuis labs/*/lab.yaml, mais pas dans le parcours "
        "recommandé, qui se construit depuis meta.yml. Un apprenant qui suit "
        "le parcours ne les jouera jamais. Ajoutez-les dans la section de leur "
        "certification, à la place que leur difficulté justifie."
    )


def test_chaque_lab_declare_existe_vraiment() -> None:
    fantomes = [lab for lab in _declares() if lab not in _sur_disque()]
    assert not fantomes, (
        "Lab(s) déclaré(s) dans meta.yml mais absent(s) de labs/ :\n  "
        + "\n  ".join(fantomes)
        + "\n\nSoit le lab a été renommé sans que meta.yml suive, soit ses "
        "fichiers ont été perdus. Le second cas est arrivé : un répertoire de "
        "lab peut survivre à une manipulation de branches avec son seul "
        "sous-dossier challenge/, ce qui ne se voit pas dans un `ls`."
    )


def test_aucun_lab_n_est_declare_deux_fois() -> None:
    """Un lab dans deux sections apparaîtrait deux fois dans le parcours, avec
    deux numéros d'ordre différents, ce qui n'a pas de sens."""
    doublons = sorted(lab for lab, n in Counter(_declares()).items() if n > 1)
    assert not doublons, (
        f"Lab(s) déclaré(s) plusieurs fois : {', '.join(doublons)}."
    )


#: Ce qu'un lab porte forcément. La liste vient du CLAUDE.md, section « Ce que
#: chaque lab doit porter », plus les deux README et les fichiers en français
#: qu'impose le catalogue bilingue.
ATTENDUS = (
    "lab.yaml",
    "lab.fr.yaml",
    "setup.yaml",
    "cleanup.yaml",
    "scenario.md",
    "scenario.fr.md",
    "README.md",
    "README.fr.md",
    "challenge/hints.yaml",
    "challenge/solution.sh",
    "challenge/tests/test_functional.py",
)


def test_aucun_repertoire_de_lab_n_est_amputé() -> None:
    """Un répertoire de lab incomplet est INVISIBLE pour le reste de
    l'outillage, et c'est ce qui le rend dangereux.

    Mesuré le 2026-09-16 : `labs/cks-rbac-least-privilege/` s'est retrouvé
    réduit à son seul sous-dossier `challenge/` après une manipulation de
    branches. `dsoxlab validate-structure` ne l'a pas signalé, et c'est
    logique : il énumère les labs par leur `lab.yaml`, donc un lab sans
    `lab.yaml` n'existe pas pour lui. `check-labs-completude.py` fait le même
    raisonnement. Le lab avait disparu du catalogue sans qu'un seul contrôle
    ne bronche.

    Ce test énumère les RÉPERTOIRES, pas les `lab.yaml`. C'est la seule façon
    de voir ce qui manque : on ne peut pas constater l'absence d'un fichier en
    partant de ce fichier.
    """
    incomplets = {}
    for repertoire in sorted(LABS.iterdir()):
        if not repertoire.is_dir() or repertoire.name.startswith("."):
            continue
        manquants = [f for f in ATTENDUS if not (repertoire / f).is_file()]
        if manquants:
            incomplets[repertoire.name] = manquants

    assert not incomplets, (
        "Répertoire(s) de lab incomplet(s) :\n"
        + "\n".join(
            f"  {nom} : il manque {', '.join(manquants)}"
            for nom, manquants in incomplets.items()
        )
        + "\n\nUn lab amputé de son lab.yaml n'est vu par AUCUN autre contrôle "
        "du dépôt : ils partent tous des lab.yaml existants. Si le répertoire "
        "est un reste à jeter, supprimez-le ; s'il s'agit d'un lab, "
        "restaurez ses fichiers depuis git."
    )
