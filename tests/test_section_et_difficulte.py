"""La section et la difficulté sont déclarées, et cohérentes.

Pourquoi ce fichier existe
--------------------------
Les deux champs manquaient aux 37 labs, et leur absence ne se voyait pas : le
moteur a des valeurs de repli qui rendent le catalogue parfaitement
fonctionnel, mais faux.

**`section` retombe sur `repo.category`.** Le code de dsoxlab le documente, avec
la mesure faite sur le catalogue Linux jumeau : « 84 labs sous une section
unique, donc un seul nœud illisible ». Ici, les 37 labs se retrouvaient dans une
section « kubernetes », et `list-labs --section cka` ne filtrait rien.

**`difficulty` vaut « beginner » par défaut.** La restauration d'etcd, le
dépannage de l'API server et le confinement AppArmor étaient donc présentés à
l'apprenant comme des exercices pour débutant.

Aucun de ces deux défauts ne fait échouer quoi que ce soit. C'est exactement
pour cela qu'ils méritent un test : un réglage faux qui n'empêche rien ne se
découvre qu'en regardant, et personne ne regarde deux fois.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

from lecture_yaml import lire_yaml  # noqa: E402

#: Les seules valeurs que dsoxlab traduit à l'affichage. Une autre s'afficherait
#: telle quelle, en anglais, au milieu d'une fiche en français.
DIFFICULTES = {"beginner", "intermediate", "advanced"}


def labs() -> list[Path]:
    return sorted((RACINE / "labs").glob("*/lab.yaml"))


def sections_declarees() -> set[str]:
    meta = lire_yaml(RACINE / "meta.yml")
    return {s["id"] for s in meta.get("sections", []) if "id" in s}


@pytest.mark.parametrize("fichier", labs(), ids=lambda p: p.parent.name)
def test_la_section_est_declaree_et_connue(fichier: Path) -> None:
    """Sans `section`, le lab tombe dans `repo.category` et le filtre ne filtre plus."""
    d = lire_yaml(fichier)
    section = d.get("section")

    assert section, (
        f"{fichier.parent.name} : aucune `section`. dsoxlab retombera sur "
        f"`repo.category` et rangera ce lab avec tous les autres, ce qui rend "
        f"`dsoxlab list-labs --section` inopérant."
    )
    assert section in sections_declarees(), (
        f"{fichier.parent.name} : section « {section} » absente de meta.yml "
        f"({', '.join(sorted(sections_declarees()))}). Une section inconnue ne "
        f"s'affiche nulle part."
    )


@pytest.mark.parametrize("fichier", labs(), ids=lambda p: p.parent.name)
def test_la_section_suit_la_certification(fichier: Path) -> None:
    """La section et le tag de certification disent la même chose.

    Les laisser diverger produirait un lab rangé sous CKA mais annoncé CKAD,
    que le catalogue des README classerait d'un côté et la CLI de l'autre.
    """
    d = lire_yaml(fichier)
    tags = d.get("certification_tags") or []
    assert tags, f"{fichier.parent.name} : aucun certification_tags"
    assert d.get("section") == tags[0], (
        f"{fichier.parent.name} : section « {d.get('section')} » mais "
        f"certification_tags {tags}. Le catalogue et la CLI se contrediraient."
    )


@pytest.mark.parametrize("fichier", labs(), ids=lambda p: p.parent.name)
def test_la_difficulte_est_declaree(fichier: Path) -> None:
    """Sans `difficulty`, tout devient « débutant », y compris la restauration d'etcd."""
    d = lire_yaml(fichier)
    difficulte = d.get("difficulty")

    assert difficulte, (
        f"{fichier.parent.name} : aucune `difficulty`. dsoxlab affichera "
        f"« débutant » par défaut — ce qu'un lab de dépannage du control plane "
        f"n'est pas."
    )
    assert difficulte in DIFFICULTES, (
        f"{fichier.parent.name} : difficulté « {difficulte} » hors de "
        f"{sorted(DIFFICULTES)}. Une autre valeur s'affiche telle quelle, en "
        f"anglais, au milieu d'une fiche française."
    )


def test_les_trois_niveaux_sont_employes() -> None:
    """Un catalogue dont tous les labs ont le même niveau n'informe pas plus
    qu'un catalogue qui n'en déclare aucun."""
    vus = {lire_yaml(f).get("difficulty") for f in labs()}
    manquants = DIFFICULTES - vus
    assert not manquants, (
        f"aucun lab n'est classé {sorted(manquants)} : la difficulté ne "
        f"distingue alors rien."
    )


def test_ce_qui_touche_au_noeud_nest_pas_debutant() -> None:
    """Le garde-fou qui porte le sens de ce fichier.

    Un lab qui restaure etcd, répare le kubelet ou charge un profil AppArmor
    demande de comprendre le nœud et son système. L'annoncer « débutant »
    envoie l'apprenant au casse-pipe, et c'est précisément ce que le défaut
    d'origine faisait.
    """
    exigeants = {
        "cka-etcd-backup-restore",
        "cka-troubleshoot-apiserver",
        "cka-troubleshoot-kubelet",
        "cka-troubleshoot-node-notready",
        "cks-apparmor-confiner-un-pod",
    }
    for fichier in labs():
        nom = fichier.parent.name
        if nom in exigeants:
            assert lire_yaml(fichier).get("difficulty") == "advanced", (
                f"{nom} touche au nœud ou au control plane : il ne peut pas "
                f"être annoncé « {lire_yaml(fichier).get('difficulty')} »."
            )
