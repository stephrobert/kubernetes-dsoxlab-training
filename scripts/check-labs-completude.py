#!/usr/bin/env python3
"""Dit ce qui reste à faire sur chaque lab, et refuse de laisser passer un
lab transposé qu'on aurait cru fini.

`dsoxlab validate-structure` vérifie le **contrat** : un lab transposé le passe
immédiatement, avec un `doc_url` bidon, un scénario en anglais et un
`cleanup.yaml` vide. Il est conforme et inutilisable. Ce contrôle regarde ce
que le contrat ne regarde pas.

    python3 scripts/check-labs-completude.py            # tableau
    python3 scripts/check-labs-completude.py --check    # exit 1 si un lab est incomplet
    python3 scripts/check-labs-completude.py --lab <id> # un seul

CE QU'IL NE PEUT PAS VÉRIFIER, et qui reste à la charge de l'auteur : qu'un
lab **joué** rende 0 avant le travail et 100 après. Aucun script ne le dira à
votre place, c'est la règle non négociable de `CONTRIBUTING.md`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"
MARQUEUR = "A_COMPLETER"

# Des mots qui ne peuvent pas se trouver dans un lab fini et francophone.
ANGLAIS = re.compile(
    r"\b(the|you must|ensure that|should be|verify that|namespace called|"
    r"make sure|following|create a|troubleshoot)\b",
    re.IGNORECASE,
)


def defauts(lab: Path) -> list[str]:
    """Tout ce qui empêche de considérer ce lab comme livrable."""
    out: list[str] = []
    fichier = lab / "lab.yaml"
    if not fichier.is_file():
        return ["lab.yaml absent"]
    d = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}

    url = str(d.get("doc_url", ""))
    if MARQUEUR in url or "example.invalid" in url or "example.org" in url:
        out.append("doc_url : la leçon du blog n'est pas renseignée")
    elif not url.startswith("https://blog.stephane-robert.info/"):
        out.append(f"doc_url : hors du blog ({url[:48]})")

    if d.get("id") != lab.name:
        out.append(f"id « {d.get('id')} » différent du répertoire « {lab.name} »")

    # Le catalogue est bilingue, anglais prioritaire : chaque document existe
    # des deux côtés. dsoxlab validate-structure refuse déjà une traduction
    # unilatérale (content_missing_english) ; ici on nomme le fichier manquant,
    # parce que ce contrôle sert à dire ce qu'il RESTE à faire.
    for nom in ("scenario.md", "scenario.fr.md", "README.md", "README.fr.md"):
        if not (lab / nom).is_file():
            out.append(f"{nom} absent")

    if not (lab / "lab.fr.yaml").is_file():
        out.append("lab.fr.yaml absent : le titre et la description ne sont pas traduits")

    for nom in ("scenario.md", "scenario.fr.md"):
        fichier = lab / nom
        if fichier.is_file() and MARQUEUR in fichier.read_text(encoding="utf-8"):
            out.append(f"{nom} : marqueur à lever")

    # Le contrôle de langue porte désormais sur la version FRANÇAISE : c'est
    # elle qui reste une copie de l'anglais tant que personne n'est passé. Le
    # `scenario.md`, lui, DOIT être en anglais.
    #
    # L'identifiant du lab apparaît dans le scénario (la commande `dsoxlab
    # check <id>`), et huit labs CKA portent « troubleshoot » dans le leur : on
    # le retire avant de chercher de l'anglais, sinon un scénario entièrement
    # français est déclaré anglais.
    scen_fr = lab / "scenario.fr.md"
    if scen_fr.is_file():
        texte = scen_fr.read_text(encoding="utf-8")
        if MARQUEUR not in texte and ANGLAIS.search(texte.replace(lab.name, "")):
            out.append("scenario.fr.md : encore en anglais, la traduction n'est pas faite")

    clean = lab / "cleanup.yaml"
    if not clean.is_file():
        out.append("cleanup.yaml absent")
    elif MARQUEUR in clean.read_text(encoding="utf-8"):
        out.append("cleanup.yaml : nettoyage à écrire")

    setup = lab / "setup.yaml"
    if setup.is_file() and MARQUEUR in setup.read_text(encoding="utf-8"):
        out.append("setup.yaml : mise en situation à confronter à la 1.37")

    hints = lab / "challenge" / "hints.yaml"
    if not hints.is_file():
        out.append("challenge/hints.yaml absent")
    else:
        h = yaml.safe_load(hints.read_text(encoding="utf-8")) or {}
        items = h.get("hints") or []
        if not items:
            out.append("hints : aucun indice")
        elif any(i.get("text_fr") == i.get("text_en") for i in items):
            out.append("hints : text_fr est encore une copie de l'anglais")

    if not (lab / "challenge" / "tests" / "test_functional.py").is_file():
        out.append("challenge/tests/test_functional.py absent")
    if not (lab / "challenge" / "solution.sh").is_file():
        out.append("challenge/solution.sh absent : rien ne prouve le lab faisable")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--check", action="store_true", help="exit 1 si un lab est incomplet")
    ap.add_argument("--lab", help="ne regarder qu'un lab")
    args = ap.parse_args()

    if not LABS.is_dir():
        print(f"labs/ introuvable sous {RACINE}", file=sys.stderr)
        return 2

    dossiers = sorted(p for p in LABS.iterdir() if (p / "lab.yaml").is_file())
    if args.lab:
        dossiers = [p for p in dossiers if p.name == args.lab]
        if not dossiers:
            print(f"lab inconnu : {args.lab}", file=sys.stderr)
            return 2

    prets, incomplets = [], []
    for lab in dossiers:
        d = defauts(lab)
        (incomplets if d else prets).append((lab.name, d))

    # Ce que scripts/valider-labs.py a mesuré : la seule preuve qu'un lab
    # livrable est aussi un lab juste.
    validations = RACINE / "validation-labs.json"
    mesures = yaml.safe_load(validations.read_text(encoding="utf-8")) if validations.is_file() else {}

    print(f"{len(dossiers)} lab(s) : {len(prets)} livrable(s), {len(incomplets)} incomplet(s)\n")

    for nom, _ in prets:
        m = mesures.get(nom)
        if m and m.get("verdict") == "VALIDE":
            print(f"  ✔ {nom}    validé le {m['date']} sur {m.get('kubernetes', '?')}")
        elif m:
            print(f"  ✔ {nom}    ROUGE le {m['date']} : {'; '.join(m.get('raisons') or [m.get('erreur', '?')])}")
        else:
            print(f"  ✔ {nom}    jamais validé")
    for nom, d in incomplets:
        print(f"\n  ✘ {nom}")
        for x in d:
            print(f"      {x}")

    if prets:
        print(
            "\n  Rappel : « livrable » ne veut pas dire « validé ». Un lab se joue,"
            "\n  et il doit rendre 0 avant le travail puis 100 après."
        )

    return 1 if (args.check and incomplets) else 0


if __name__ == "__main__":
    sys.exit(main())
