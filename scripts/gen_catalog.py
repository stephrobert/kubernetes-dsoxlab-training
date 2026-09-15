#!/usr/bin/env python3
"""Génère la table des labs des README à partir des `lab.yaml` réels.

Un catalogue écrit à la main se périme en silence : un lab renommé, et le
README annonce un identifiant qui n'existe plus. Ici la source de vérité est
`labs/*/lab.yaml`, et le hook `pre-push` refuse un README périmé.

Les deux langues sont générées : `README.md` depuis `lab.yaml`, `README.fr.md`
depuis `lab.fr.yaml`, qui surcharge le titre et la description. Un lab dont le
`lab.fr.yaml` manque apparaîtrait en anglais dans la table française, ce qui se
verrait : `dsoxlab validate-structure` le refuse d'ailleurs avant, avec
`content_missing_english`.

Les labs sont groupés par CERTIFICATION (`certification_tags`), puis triés par
domaine du blueprint (`level`) : c'est ainsi que se lit la seule question qui
pilote ce dépôt, « combien de compétences de l'examen puis-je démontrer ? ».

La colonne de validation vient de `validation-labs.json`, écrit par
`scripts/valider-labs.py`. Un lab livrable n'est pas un lab validé, et cette
distinction est la doctrine du dépôt : elle doit se voir dans le catalogue.

Usage :
    python3 scripts/gen_catalog.py            # régénère les deux README
    python3 scripts/gen_catalog.py --check    # sort en 1 si un README est périmé
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

# Un seul chemin de lecture pour tout le catalogue : voir scripts/lecture_yaml.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lecture_yaml import YamlIllisible, lire_yaml

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"
VALIDATION = RACINE / "validation-labs.json"
DEBUT, FIN = "<!-- LABS:START -->", "<!-- LABS:END -->"

#: Ordre d'affichage des certifications, et leur titre. Repris de `meta.yml`,
#: qui les déclare dans cet ordre. Le titre est le même dans les deux langues :
#: ce sont les noms officiels des certifications.
CERTIFICATIONS = [
    ("cka", "CKA, Certified Kubernetes Administrator"),
    ("ckad", "CKAD, Certified Kubernetes Application Developer"),
    ("cks", "CKS, Certified Kubernetes Security Specialist"),
]

#: Le curriculum de référence, et la version de Kubernetes réellement jouée.
#:
#: Ce sont DEUX choses différentes, et les confondre trompe le lecteur. Le
#: curriculum est ce que la CNCF publie et sur quoi l'examen porte ; le runtime
#: est ce sur quoi les labs ont été validés ici. Le second avance plus vite que
#: le premier : au 2026-09-15, les labs tournent sur Kubernetes 1.37 alors que
#: les curriculums publiés sont CKA/CKAD v1.35 et CKS v1.34.
#:
#: Cette information ne peut pas vivre dans meta.yml : son contrat rejette
#: toute clé qu'il ne connaît pas, et `validate-structure` échoue. Vérifié.
CURRICULUMS = {
    "cka": "v1.35",
    "ckad": "v1.35",
    "cks": "v1.34",
}
CURRICULUM_SOURCE = "https://github.com/cncf/curriculum"

LANGUES = {
    "en": {
        "fichier": "README.md",
        "colonnes": ("Lab", "Title", "Blueprint domain", "Duration", "Validated", "Companion lesson"),
        "compte": "{n} lab(s).",
        "lecon": "lesson",
        "aucune": "none",
        "non": "no",
        "rouge": "**RED**",
        "capstone": "capstone, several domains",
        "pied": (
            "Total: **{n} lab(s)**. The validation column carries the date of the "
            "last run of `scripts/valider-labs.py`, which plays the lab in both "
            "directions and checks that it leaves no trace. A shippable lab is not "
            "a validated lab.\n\n"
            "**Runtime validated: Kubernetes {k8s}.** "
            "**Reference curriculum: {curriculums}** "
            "([cncf/curriculum]({source})). The two move at different speeds: the "
            "labs run on a newer Kubernetes than the published exam curriculum, "
            "which is why they are stated separately rather than as one version."
        ),
    },
    "fr": {
        "fichier": "README.fr.md",
        "colonnes": ("Lab", "Titre", "Domaine du blueprint", "Durée", "Validé", "Leçon jumelée"),
        "compte": "{n} lab(s).",
        "lecon": "leçon",
        "aucune": "aucune",
        "non": "non",
        "rouge": "**ROUGE**",
        "capstone": "capstone, plusieurs domaines",
        "pied": (
            "Total : **{n} lab(s)**. La colonne « Validé » porte la date du dernier "
            "passage de `scripts/valider-labs.py`, qui joue le lab dans les deux "
            "sens et vérifie qu'il ne laisse aucune trace. Un lab livrable n'est "
            "pas un lab validé.\n\n"
            "**Runtime validé : Kubernetes {k8s}.** "
            "**Curriculum de référence : {curriculums}** "
            "([cncf/curriculum]({source})). Les deux n'avancent pas à la même "
            "vitesse : les labs tournent sur un Kubernetes plus récent que le "
            "curriculum publié, et les annoncer séparément évite de laisser croire "
            "que l'examen porte sur la version du runtime."
        ),
    },
}


@lru_cache(maxsize=1)
def _labs_caches() -> tuple[dict, ...]:
    """Mémorise la lecture : `_labs()` est appelé une fois par README.

    Sans ce cache, un lab illisible était signalé TROIS fois pour une seule
    faute. Un message répété se lit comme trois problèmes, et on cherche les
    deux autres.
    """
    return tuple(_labs_sans_cache())


def _labs() -> list[dict]:
    # Copie superficielle : les appelants enrichissent les dictionnaires, et le
    # cache ne doit pas se faire modifier sous les pieds.
    return [dict(lab) for lab in _labs_caches()]


def _labs_sans_cache() -> list[dict]:
    """Chaque lab, avec son titre dans les deux langues.

    Un lab dont le YAML est illisible est ÉCARTÉ du catalogue, avec un message
    sur la sortie d'erreur. Il ne fait pas tomber la génération : le README doit
    rester générable, et c'est `check-labs-completude.py` qui a pour rôle de
    refuser le lab fautif. Deux outils, deux responsabilités.
    """
    trouves = []
    for fichier in sorted(LABS.glob("*/lab.yaml")):
        try:
            donnees = lire_yaml(fichier)
        except YamlIllisible as exc:
            print(
                f"  lab écarté du catalogue — {fichier.parent.name}/{exc}",
                file=sys.stderr,
            )
            continue
        donnees["_repertoire"] = fichier.parent.name
        donnees["_titre_en"] = str(donnees.get("title", "")).strip('"')
        surcharge = fichier.parent / "lab.fr.yaml"
        if surcharge.is_file():
            try:
                fr = lire_yaml(surcharge)
            except YamlIllisible as exc:
                print(f"  {fichier.parent.name}/{exc}", file=sys.stderr)
                fr = {}
            donnees["_titre_fr"] = str(fr.get("title", donnees["_titre_en"])).strip('"')
        else:
            donnees["_titre_fr"] = donnees["_titre_en"]
        trouves.append(donnees)
    return trouves


def _version_kubernetes(mesures: dict[str, dict]) -> str:
    """La version RÉELLEMENT jouée, lue dans validation-labs.json.

    Elle n'est pas écrite à la main : une version annoncée qui ne serait plus
    celle des validations serait pire que pas de version du tout. Plusieurs
    versions coexistant, on les rend toutes plutôt que d'en choisir une.
    """
    versions = sorted({str(m.get("kubernetes", "")) for m in mesures.values() if m.get("kubernetes")})
    if not versions:
        return "non mesuré"
    return ", ".join(versions)


def _validations() -> dict[str, dict]:
    if not VALIDATION.is_file():
        return {}
    return json.loads(VALIDATION.read_text(encoding="utf-8"))


def _cellule_validation(lab: dict, mesures: dict[str, dict], mots: dict) -> str:
    mesure = mesures.get(str(lab.get("id", "")))
    if not mesure:
        return str(mots["non"])
    if mesure.get("verdict") != "VALIDE":
        return str(mots["rouge"])
    return str(mesure.get("date", ""))[:10]


def _table(langue: str) -> str:
    mots = LANGUES[langue]
    labs = _labs()
    mesures = _validations()
    lignes: list[str] = []

    for tag, titre in CERTIFICATIONS:
        # Les capstones passent en dernier, et ce n'est pas cosmétique : ils
        # supposent les micro-labs de leur certification déjà joués, puisqu'ils
        # ne disent plus quel objet employer ni où est la panne. Les lire en
        # tête du tableau enverrait l'apprenant au mur.
        de_cette_certif = sorted(
            (lab for lab in labs if tag in (lab.get("certification_tags") or [])),
            key=lambda lab: (
                lab.get("lab_type") == "capstone",
                str(lab.get("level", "")),
                str(lab.get("id", "")),
            ),
        )
        if not de_cette_certif:
            continue
        lignes.append(f"### {titre}")
        lignes.append("")
        lignes.append(str(mots["compte"]).format(n=len(de_cette_certif)))
        lignes.append("")
        lignes.append("| " + " | ".join(mots["colonnes"]) + " |")
        lignes.append("|" + "|".join(["---"] * len(mots["colonnes"])) + "|")
        for lab in de_cette_certif:
            url = str(lab.get("doc_url", ""))
            # Un capstone ne vise pas UN domaine du blueprint, il en croise
            # plusieurs : afficher son `level` seul laisserait croire qu'il
            # n'éprouve que celui-là, alors que c'est un examen blanc.
            capstone = lab.get("lab_type") == "capstone"
            lignes.append(
                "| [`{id}`](labs/{rep}/) | {titre} | {niveau} | {duree} | {valide} | {lecon} |".format(
                    id=lab.get("id", ""),
                    rep=lab["_repertoire"],
                    titre=lab["_titre_fr"] if langue == "fr" else lab["_titre_en"],
                    niveau=mots["capstone"] if capstone else lab.get("level", ""),
                    duree=lab.get("estimated_time", ""),
                    valide=_cellule_validation(lab, mesures, mots),
                    lecon=f"[{mots['lecon']}]({url})" if url else mots["aucune"],
                )
            )
        lignes.append("")

    lignes.append(
        str(mots["pied"]).format(
            n=len(labs),
            k8s=_version_kubernetes(mesures),
            curriculums=", ".join(f"{c.upper()} {v}" for c, v in CURRICULUMS.items()),
            source=CURRICULUM_SOURCE,
        )
    )
    return "\n".join(lignes)


def _rendu(langue: str) -> tuple[Path, str]:
    fichier = RACINE / str(LANGUES[langue]["fichier"])
    contenu = fichier.read_text(encoding="utf-8")
    if DEBUT not in contenu or FIN not in contenu:
        sys.exit(
            f"{fichier.name} ne porte pas les marqueurs {DEBUT} / {FIN} : "
            "le catalogue ne sait pas où s'écrire."
        )
    avant = contenu.split(DEBUT)[0]
    apres = contenu.split(FIN)[1]
    return fichier, f"{avant}{DEBUT}\n\n{_table(langue)}\n\n{FIN}{apres}"


def main() -> int:
    rendus = [_rendu(langue) for langue in LANGUES]

    if "--check" in sys.argv:
        perimes = [f.name for f, attendu in rendus if f.read_text(encoding="utf-8") != attendu]
        if perimes:
            print(
                f"Catalogue périmé dans : {', '.join(perimes)}.\n"
                "Régénérez-le avec : python3 scripts/gen_catalog.py",
                file=sys.stderr,
            )
            return 1
        print(f"Catalogue à jour dans les deux langues ({len(_labs())} labs).")
        return 0

    for fichier, attendu in rendus:
        fichier.write_text(attendu, encoding="utf-8")
    print(f"README.md et README.fr.md régénérés ({len(_labs())} labs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
