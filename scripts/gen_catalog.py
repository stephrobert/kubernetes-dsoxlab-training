#!/usr/bin/env python3
"""Génère la table des labs du README à partir des `lab.yaml` réels.

Un catalogue écrit à la main se périme en silence : un lab renommé, et le
README annonce un identifiant qui n'existe plus. Ici la source de vérité est
`labs/*/lab.yaml`, et le hook `pre-push` refuse un README périmé.

Les labs sont groupés par CERTIFICATION (`certification_tags`), puis triés par
domaine du blueprint (`level`) : c'est ainsi que se lit la seule question qui
pilote ce dépôt, « combien de compétences de l'examen puis-je démontrer ? ».

La colonne « Validé » vient de `validation-labs.json`, écrit par
`scripts/valider-labs.py`. Un lab livrable n'est pas un lab validé, et cette
distinction est la doctrine du dépôt : elle doit se voir dans le catalogue.

Usage :
    python3 scripts/gen_catalog.py            # régénère le README
    python3 scripts/gen_catalog.py --check    # sort en 1 si le README est périmé
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"
README = RACINE / "README.md"
VALIDATION = RACINE / "validation-labs.json"
DEBUT, FIN = "<!-- LABS:START -->", "<!-- LABS:END -->"

#: Ordre d'affichage des certifications, et leur titre. Repris de `meta.yml`,
#: qui les déclare dans cet ordre.
CERTIFICATIONS = [
    ("cka", "CKA, Certified Kubernetes Administrator"),
    ("ckad", "CKAD, Certified Kubernetes Application Developer"),
    ("cks", "CKS, Certified Kubernetes Security Specialist"),
]

COLONNES = ("Lab", "Titre", "Domaine du blueprint", "Durée", "Validé", "Leçon jumelée")


def _labs() -> list[dict]:
    """Chaque `lab.yaml` du catalogue, chemin du répertoire compris."""
    trouves = []
    for fichier in sorted(LABS.glob("*/lab.yaml")):
        donnees = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}
        donnees["_repertoire"] = fichier.parent.name
        trouves.append(donnees)
    return trouves


def _validations() -> dict[str, dict]:
    if not VALIDATION.is_file():
        return {}
    return json.loads(VALIDATION.read_text(encoding="utf-8"))


def _cellule_validation(lab: dict, mesures: dict[str, dict]) -> str:
    mesure = mesures.get(str(lab.get("id", "")))
    if not mesure:
        return "non"
    if mesure.get("verdict") != "VALIDE":
        return "**ROUGE**"
    return str(mesure.get("date", "oui"))[:10]


def _table() -> str:
    labs = _labs()
    mesures = _validations()
    lignes: list[str] = []

    for tag, titre in CERTIFICATIONS:
        de_cette_certif = sorted(
            (lab for lab in labs if tag in (lab.get("certification_tags") or [])),
            key=lambda lab: (str(lab.get("level", "")), str(lab.get("id", ""))),
        )
        if not de_cette_certif:
            continue
        lignes.append(f"### {titre}")
        lignes.append("")
        lignes.append(f"{len(de_cette_certif)} lab(s).")
        lignes.append("")
        lignes.append("| " + " | ".join(COLONNES) + " |")
        lignes.append("|" + "|".join(["---"] * len(COLONNES)) + "|")
        for lab in de_cette_certif:
            url = str(lab.get("doc_url", ""))
            lignes.append(
                "| [`{id}`](labs/{rep}/) | {titre} | {niveau} | {duree} | {valide} | {lecon} |".format(
                    id=lab.get("id", ""),
                    rep=lab["_repertoire"],
                    titre=str(lab.get("title", "")).strip('"'),
                    niveau=lab.get("level", ""),
                    duree=lab.get("estimated_time", ""),
                    valide=_cellule_validation(lab, mesures),
                    lecon=f"[leçon]({url})" if url else "aucune",
                )
            )
        lignes.append("")

    lignes.append(
        f"Total : **{len(labs)} lab(s)**. La colonne « Validé » porte la date du "
        "dernier passage de `scripts/valider-labs.py`, qui joue le lab dans les "
        "deux sens et vérifie qu'il ne laisse aucune trace. Un lab livrable n'est "
        "pas un lab validé."
    )
    return "\n".join(lignes)


def _rendu() -> str:
    contenu = README.read_text(encoding="utf-8")
    if DEBUT not in contenu or FIN not in contenu:
        sys.exit(
            f"README.md ne porte pas les marqueurs {DEBUT} / {FIN} : "
            "le catalogue ne sait pas où s'écrire."
        )
    avant = contenu.split(DEBUT)[0]
    apres = contenu.split(FIN)[1]
    return f"{avant}{DEBUT}\n\n{_table()}\n\n{FIN}{apres}"


def main() -> int:
    attendu = _rendu()
    if "--check" in sys.argv:
        if README.read_text(encoding="utf-8") != attendu:
            print(
                "README.md est périmé : le catalogue ne correspond plus aux "
                "lab.yaml.\nRégénérez-le avec : python3 scripts/gen_catalog.py",
                file=sys.stderr,
            )
            return 1
        print(f"README.md à jour ({len(_labs())} labs).")
        return 0

    README.write_text(attendu, encoding="utf-8")
    print(f"README.md régénéré ({len(_labs())} labs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
