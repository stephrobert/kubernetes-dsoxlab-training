#!/usr/bin/env python3
"""Transpose un lab de K8sExamLab vers le contrat dsoxlab courant.

K8sExamLab est l'ancêtre archivé de dsoxlab : moteur et labs y vivaient
ensemble. Ses **61 labs CKA/CKAD/CKS** sont rejetés par le moteur 0.1.85
(`runtime` y est une chaîne, c'est un mapping désormais), mais leur substance
est intacte et transposable.

CE QUI SE TRANSPOSE TOUT SEUL
    domain            -> level
    tags              -> skills
    duration_minutes  -> estimated_time
    description+instructions -> scenario.md
    checks[]          -> un test pytest par check, qui appelle la bibliothèque
                         de checks héritée, conservée telle quelle
    hints[]           -> challenge/hints.yaml, le contenu est DÉJÀ en base64
                         et `penalty` devient `cost`
    setup.scripts     -> setup.yaml, une tâche qui joue le script
    solution/         -> challenge/solution.sh

CE QUE PERSONNE NE PEUT GÉNÉRER, et que le script marque explicitement
    doc_url           la leçon du blog que le lab éprouve
    text_fr           la traduction des indices
    cleanup.yaml      n'existe pas dans l'ancien format
    la validation en 1.37, puisque ces labs visent 1.34

Le script ne prétend donc pas finir le travail : il fait la partie mécanique et
**laisse des marqueurs A_COMPLETER** là où un humain doit passer. Un lab converti
n'est pas un lab validé.

    python3 scripts/convertir-k8sexamlab.py --lab labs/cka/troubleshooting/troubleshoot-dns
    python3 scripts/convertir-k8sexamlab.py --tous --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
SOURCE = Path.home() / "Projets" / "K8sExamLab"
MARQUEUR = "A_COMPLETER"

# Les domaines de l'ancien format sont déjà les domaines des blueprints : ils
# deviennent le `level` sans traduction.
SECTIONS = {"cka": "cka", "ckad": "ckad", "cks": "cks"}


def charger(chemin: Path) -> dict:
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))


def scenario(vieux: dict) -> str:
    """Le scénario reprend description et instructions, en signalant la langue.

    On ne traduit pas automatiquement : une consigne d'examen mal traduite est
    pire qu'une consigne en anglais, parce qu'elle se lit sans méfiance.
    """
    ident = f"{SECTIONS.get(vieux.get('category', ''), 'cka')}-{vieux['id']}"
    return f"""# {vieux['title']}

<!-- {MARQUEUR} : ce scénario vient de K8sExamLab et il est EN ANGLAIS.
     À réécrire en français, et à confronter à Kubernetes 1.37 : ce lab visait
     la {vieux.get('kubernetes_version', '1.34')}. -->

## La situation

{vieux.get('description', '').strip()}

## Ce que vous devez obtenir

{vieux.get('instructions', '').strip()}

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, pas les commandes tapées.

```bash
dsoxlab check {ident}
```
"""


def lab_yaml(vieux: dict, section: str) -> dict:
    minutes = vieux.get("duration_minutes", 30)
    return {
        # L'identifiant porte l'examen, comme le repertoire : deux labs peuvent
        # traiter le meme sujet pour deux certifications differentes, et un id
        # qui diverge du repertoire rend « dsoxlab run » deroutant.
        "id": f"{section}-{vieux['id']}",
        "title": vieux["title"],
        "level": vieux.get("domain", section),
        "description": (vieux.get("description", "").strip().splitlines() or [""])[0],
        "skills": vieux.get("tags") or [section],
        "distros": ["ubuntu24"],
        "doc_url": f"https://example.invalid/{MARQUEUR}",
        "lab_type": "lab",
        "estimated_time": f"{minutes}m",
        "certification_tags": [section],
        "runtime": {
            "type": "vm",
            "targets": [{"name": "cp", "host": "k8s-cp.lab"}],
            "default": "cp",
        },
        "validation": {"functional": True, "persistence_after_reboot": False},
    }


def hints_yaml(vieux: dict) -> dict:
    """Les indices sont DÉJÀ en base64 : seule la langue manque.

    On recopie le contenu anglais dans les deux champs plutôt que de laisser
    `text_fr` vide, qui afficherait du blanc à l'apprenant. Le marqueur est
    dans le lab.yaml, pas ici, parce qu'un base64 marqué serait illisible.
    """
    # Un lab hérité, rolling-update-strategy, a deux tags mal indentés dans sa
    # liste d'indices : des chaînes au milieu des mappings. On ne garde que
    # les mappings, et on le dit, plutôt que de planter.
    indices = vieux.get("hints") or []
    ignores = [h for h in indices if not isinstance(h, dict)]
    if ignores:
        print(f"      hints : {len(ignores)} entrée(s) ignorée(s), pas des indices : {ignores}")
    return {
        "points": 100,
        "hints": [
            {
                "text_fr": h["content"],
                "text_en": h["content"],
                "cost": h.get("penalty", 10),
            }
            for h in indices
            if isinstance(h, dict)
        ],
    }


def tests_py(vieux: dict) -> str:
    """Un squelette de tests, un par check hérité, À ÉCRIRE.

    CE QUE CETTE FONCTION NE FAIT PLUS, et pourquoi.

    Jusqu'au 2026-09-15 elle produisait des tests qui appelaient la
    bibliothèque héritée déposée sous `/opt/checks` sur le nœud. C'était un
    gain apparent, et deux défauts réels :

    - le lab fini dépendait d'un reste de l'ancêtre archivé, déposé par son
      setup : une pièce de plus à maintenir, invisible depuis le test et
      introuvable pour qui le lit. Le dernier lab à en dépendre a été réécrit,
      et la règle est sans exception ;
    - le gabarit concaténait `stdout + stderr` pour décider. C'est exactement
      le défaut qui a fait passer `cka-troubleshoot-dns` AVANT le travail : le
      client SSH écrit un avertissement sur stderr, la chaîne n'est jamais
      vide, et un test qui conclut « chaîne vide = absent » conclut toujours
      « présent ».

    Le squelette produit ici ne prétend donc plus vérifier quoi que ce soit. Il
    conserve la SUBSTANCE du check hérité, sa description et ses arguments, et
    il échoue bruyamment tant qu'un humain n'a pas écrit la mesure. Un lab
    transposé qui passerait ses tests sans que personne ne les ait écrits
    serait le pire des deux mondes.

    La bibliothèque héritée reste lisible sous `shared/checks/` : elle sert de
    RÉFÉRENCE pour savoir ce que chaque check vérifiait, jamais de dépendance
    d'exécution.
    """
    corps = [
        '"""test_functional.py : squelette transposé de K8sExamLab, À ÉCRIRE.\n',
        "Chaque test porte la description du check hérité et ses arguments, et",
        "rien d'autre : la mesure est à écrire, en interrogeant le cluster avec",
        "kubectl. Tant qu'elle ne l'est pas, le test échoue, et c'est voulu.",
        "",
        "La règle du dépôt : on lit l'état du système, jamais les commandes",
        "tapées, et on décide sur la SORTIE STANDARD. stderr sert aux messages",
        "d'erreur, pas à trancher : le client SSH y écrit un avertissement, et",
        "un test qui concatène les deux ne mesure plus rien.",
        "",
        "Ce que vérifiait chaque check hérité se relit dans `shared/checks/`.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import pytest",
        "",
        "from conftest import lab_host, lab_target_host",
        "",
        'KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"',
        "",
        "",
        '@pytest.fixture(scope="module")',
        "def host():",
        '    return lab_host(lab_target_host("k8s-cp.lab"))',
        "",
        "",
        "def _kubectl(host, args: str):",
        '    """Joue une commande kubectl sur le control plane.',
        "",
        "    Rend (code, sortie standard, diagnostic), et les trois restent",
        "    SÉPARÉS. Ne jamais les concaténer pour décider.",
        '    """',
        '    res = host.run(f"sudo {KUBECTL} {args}")',
        "    return res.rc, res.stdout.strip(), res.stderr.strip()",
        "",
    ]
    for c in vieux.get("checks", []):
        nom = c["id"].replace("-", "_")
        # La VIRGULE est indispensable : Python concatene les litteraux
        # adjacents, et « "a" "b" » devient un seul argument « ab ». Le
        # defaut ne se voit pas sur un check a un seul argument.
        args = ", ".join(f'"{a}"' for a in c.get("args", []))
        desc = c.get("description", "").replace('"', "'")
        corps += [
            "",
            f"def test_{nom}(host):",
            f'    """{desc}',
            "",
            f"    Check hérité : {c['id']}({args})",
            '    """',
            f'    pytest.fail(',
            f'        "A_COMPLETER : écrire la mesure de « {desc} ». "',
            f'        "Le check hérité s\'appelait {c["id"]} avec les arguments "',
            f'        "ci-dessus ; shared/checks/ dit ce qu\'il vérifiait."',
            "    )",
        ]
    return "\n".join(corps) + "\n"


def setup_yaml(vieux: dict, a_un_script: bool) -> str:
    taches = [
        """    - name: Installer le socle, un cluster kubeadm à un nœud
      ansible.builtin.include_tasks: ../../shared/kubeadm-cluster.yml""",
    ]
    if a_un_script:
        taches.append(
            """
    - name: Poser la situation du lab
      ansible.builtin.script: fixtures/prepare.sh
      args:
        executable: /bin/bash
      environment:
        KUBECONFIG: /etc/kubernetes/admin.conf"""
        )
    return (
        "---\n"
        f"# Transposé de K8sExamLab. {MARQUEUR} : relire le script de mise en\n"
        "# situation, il vise Kubernetes "
        f"{vieux.get('kubernetes_version', '1.34')} et non 1.37.\n"
        f"- name: Préparer le lab {vieux['id']}\n"
        "  hosts: lab_target\n"
        "  become: true\n"
        "  tasks:\n" + "\n".join(taches) + "\n"
    )


def cleanup_yaml(vieux: dict) -> str:
    return (
        "---\n"
        f"# {MARQUEUR} : l'ancien format n'avait PAS de nettoyage. Lister ici ce\n"
        "# que le lab crée, namespaces compris. Le cluster, lui, reste en place.\n"
        f"- name: Nettoyer le lab {vieux['id']}\n"
        "  hosts: lab_target\n"
        "  become: true\n"
        "  tasks:\n"
        f"    - name: {MARQUEUR} supprimer les objets créés par ce lab\n"
        "      ansible.builtin.debug:\n"
        f'        msg: "Nettoyage à écrire pour {vieux["id"]}"\n'
    )


def convertir(src: Path, dry: bool) -> tuple[str, list[str]]:
    vieux = charger(src / "lab.yaml")
    section = SECTIONS.get(vieux.get("category", ""), "cka")
    dest = RACINE / "labs" / f"{section}-{vieux['id']}"
    a_completer = [
        "doc_url : la leçon du blog que ce lab éprouve",
        "scenario.md : à réécrire en français",
        "hints : text_fr est une copie de l'anglais",
        "cleanup.yaml : à écrire, l'ancien format n'en avait pas",
        f"validation en 1.37 : ce lab visait {vieux.get('kubernetes_version')}",
    ]
    if dry:
        return dest.name, a_completer

    (dest / "challenge" / "tests").mkdir(parents=True, exist_ok=True)
    (dest / "lab.yaml").write_text(
        yaml.dump(lab_yaml(vieux, section), allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    (dest / "scenario.md").write_text(scenario(vieux), encoding="utf-8")
    (dest / "challenge" / "hints.yaml").write_text(
        yaml.dump(hints_yaml(vieux), allow_unicode=True, sort_keys=False, width=10000),
        encoding="utf-8",
    )
    (dest / "challenge" / "tests" / "test_functional.py").write_text(
        tests_py(vieux), encoding="utf-8"
    )

    prep = src / "setup" / "prepare.sh"
    if prep.is_file():
        (dest / "fixtures").mkdir(exist_ok=True)
        shutil.copy(prep, dest / "fixtures" / "prepare.sh")
    (dest / "setup.yaml").write_text(setup_yaml(vieux, prep.is_file()), encoding="utf-8")
    (dest / "cleanup.yaml").write_text(cleanup_yaml(vieux), encoding="utf-8")

    # Le repertoire solution/ peut porter des fichiers COMPAGNONS, un
    # solution.yaml le plus souvent, que le script appelle par un chemin relatif
    # a lui-meme. Ne copier que le .sh produit un « path does not exist » a
    # l'execution : constate sur troubleshoot-dns.
    sol_dir = src / "solution"
    if (sol_dir / "solution.sh").is_file():
        for f in sorted(sol_dir.iterdir()):
            if f.is_file():
                shutil.copy(f, dest / "challenge" / f.name)
        (dest / "challenge" / "solution.sh").chmod(0o755)

    (dest / "README.md").write_text(
        f"# {vieux['title']}\n\n"
        f"Transposé de K8sExamLab le 2026-09-14. **Non validé** : voir les\n"
        f"marqueurs `{MARQUEUR}`.\n\n"
        f"Examen {section.upper()}, domaine `{vieux.get('domain')}`.\n",
        encoding="utf-8",
    )
    return dest.name, a_completer


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--lab", help="chemin d'un lab dans K8sExamLab")
    ap.add_argument("--tous", action="store_true", help="les 61 labs k8s")
    ap.add_argument("--dry-run", action="store_true", help="n'écrit rien")
    args = ap.parse_args()

    if not SOURCE.is_dir():
        print(f"source introuvable : {SOURCE}", file=sys.stderr)
        return 2

    if args.tous:
        sources = [
            p.parent
            for s in ("cka", "ckad", "cks")
            for p in sorted((SOURCE / "labs" / s).rglob("lab.yaml"))
        ]
    elif args.lab:
        sources = [Path(args.lab) if Path(args.lab).is_absolute() else SOURCE / args.lab]
    else:
        ap.error("--lab ou --tous")

    total_a_faire = 0
    for s in sources:
        nom, reste = convertir(s, args.dry_run)
        total_a_faire += len(reste)
        print(f"  {'(à blanc) ' if args.dry_run else ''}{nom}")
        if len(sources) == 1:
            for r in reste:
                print(f"      {MARQUEUR} : {r}")

    print(
        f"\n  {len(sources)} lab(s) transposé(s), "
        f"{total_a_faire} point(s) à compléter à la main."
    )
    print("  Un lab transposé n'est pas un lab validé : le rejouer sur 1.37.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
