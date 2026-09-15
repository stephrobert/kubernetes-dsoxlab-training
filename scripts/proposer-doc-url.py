#!/usr/bin/env python3
"""Propose, pour chaque lab de K8sExamLab, la leçon du blog qui lui correspond.

`doc_url` est le champ que le convertisseur ne peut pas deviner, et c'est le
plus coûteux à renseigner à la main sur 61 labs : il faut connaître les 102
leçons de la formation.

Ce script fait le rapprochement par les **mots** : les `tags` et le `title` du
lab contre le titre et le slug de chaque leçon. Il ne décide pas, il
**propose**, et il affiche le score pour qu'on voie tout de suite quelles
propositions sont sûres et lesquelles demandent un arbitrage.

    python3 scripts/proposer-doc-url.py                  # tableau lisible
    python3 scripts/proposer-doc-url.py --json > m.json  # pour un script

Un lab sans correspondance franche n'est pas un problème : il signale souvent
que **la formation n'a pas de leçon sur ce sujet**, ce qui est une information
en soi, et qui remonte au backlog du blog plutôt qu'à celui-ci.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

SOURCE = Path.home() / "Projets" / "K8sExamLab"
PARCOURS = Path.home() / "Projets" / "test-astro-5" / "src/data/parcours/kubernetes.yaml"
BLOG = "https://blog.stephane-robert.info"

# Au-dessous de ce score, la proposition se relit avant d'être retenue.
SUR = 3


def mots(texte: str) -> set[str]:
    """Les mots significatifs d'un libellé, sans accent ni bruit."""
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    vides = {
        "les", "des", "une", "aux", "avec", "pour", "dans", "son", "ses", "sur",
        "the", "and", "for", "with", "your", "from", "que", "qui", "est", "par",
        "kubernetes", "k8s", "lab", "essential", "cka", "ckad", "cks",
    }
    return {m for m in re.findall(r"[a-z0-9]+", t) if len(m) > 2 and m not in vides}


def lecons() -> list[tuple[str, str, str]]:
    d = yaml.safe_load(PARCOURS.read_text(encoding="utf-8"))
    return [
        (lecon["title"], lecon["href"], m["id"])
        for m in d["modules"]
        for lecon in m.get("lessons", [])
    ]


def labs() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(SOURCE / "labs" / "*" / "*" / "*" / "lab.yaml"))):
        if not any(f"/{s}/" in f for s in ("cka", "ckad", "cks")):
            continue
        d = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        d["_chemin"] = str(Path(f).parent.relative_to(SOURCE))
        out.append(d)
    return out


def apparier(lab: dict, cibles: list[tuple[str, str, str]]):
    """Rend (score, titre, url) de la meilleure leçon, ou None."""
    # Les tags portent le sens du lab, le titre le confirme. On additionne,
    # ce qui favorise une leçon qui correspond sur les deux.
    cles = mots(" ".join(lab.get("tags") or [])) | mots(lab.get("title", ""))
    cles |= mots(lab.get("domain", "").replace("-", " "))
    meilleur = None
    for titre, href, _module in cibles:
        candidat = mots(titre) | mots(href.replace("/", " ").replace("-", " "))
        score = len(cles & candidat)
        if meilleur is None or score > meilleur[0]:
            meilleur = (score, titre, href)
    return meilleur if meilleur and meilleur[0] > 0 else None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--json", action="store_true", help="sortie machine")
    args = ap.parse_args()

    if not SOURCE.is_dir() or not PARCOURS.is_file():
        print("source ou parcours introuvable", file=sys.stderr)
        return 2

    cibles = lecons()
    resultats = []
    for lab in labs():
        prop = apparier(lab, cibles)
        resultats.append(
            {
                "lab": lab["id"],
                "chemin": lab["_chemin"],
                "examen": lab.get("category"),
                "domaine": lab.get("domain"),
                "score": prop[0] if prop else 0,
                "lecon": prop[1] if prop else None,
                "doc_url": (BLOG + prop[2]) if prop else None,
            }
        )

    if args.json:
        print(json.dumps(resultats, ensure_ascii=False, indent=2))
        return 0

    surs = [r for r in resultats if r["score"] >= SUR]
    faibles = [r for r in resultats if 0 < r["score"] < SUR]
    orphelins = [r for r in resultats if r["score"] == 0]

    print(f"{len(resultats)} labs appariés contre {len(cibles)} leçons\n")
    print(f"  {len(surs)} proposition(s) franche(s), score >= {SUR}")
    print(f"  {len(faibles)} à relire, score faible")
    print(f"  {len(orphelins)} sans correspondance\n")

    for titre, lot in (
        (f"Propositions franches (score >= {SUR})", surs),
        ("À relire avant de retenir", faibles),
        ("Sans correspondance : la formation n'a peut-être pas la leçon", orphelins),
    ):
        if not lot:
            continue
        print(f"\n== {titre}\n")
        for r in sorted(lot, key=lambda x: (-x["score"], x["lab"])):
            print(f"  [{r['score']}] {r['examen']:<5} {r['lab'][:34]:<34} -> {r['lecon'] or 'aucune'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
