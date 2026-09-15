"""Les pièges que ce dépôt a payés au moins une fois, rendus détectables.

`CLAUDE.md` les documente ; ce module les mesure. Chacun a coûté un cycle de
validation complet, c'est-à-dire de dix à vingt minutes de cluster, et aucun ne
se voit à la relecture : ils se manifestent tous comme autre chose.

1. **Un `ssh` sans `-n` dans une solution.** La solution du formateur est lue
   par `bash -s` depuis l'entrée standard. Un `ssh` sans `-n` avale le reste du
   script comme entrée : rien après lui ne s'exécute, et le script rend 0. La
   validation annonce alors « la solution ne fait pas passer les tests », ce qui
   envoie chercher un défaut dans les tests.

2. **Un `prepare.sh` qui ne trace pas.** dsoxlab ne rend que « non-zero return
   code » quand un script de fixture échoue. Sans le journal sur le nœud, le
   validateur n'a rien à relire et le diagnostic repart de zéro.

3. **Un `setup.yaml` qui n'inclut pas le socle.** Il n'y a aucun point
   d'accroche après le provisionnement (dsoxlab#213) : le cluster n'existe que
   parce que chaque lab l'installe. Un lab qui oublie l'inclusion tourne tant
   qu'un autre lab est passé avant, et échoue seul sur un cluster neuf.

5. **Un test qui décide sur `stdout + stderr`.** Le client SSH écrit
   « Warning: Permanently added '10.10.50.11' (ED25519) to the list of known
   hosts. » sur stderr. Un test qui concatène les deux flux puis conclut
   « chaîne vide = objet absent » conclut donc TOUJOURS l'inverse : la chaîne
   n'est jamais vide. Mesuré le 2026-09-15 sur le lab DNS réécrit — il passait
   AVANT le travail, sur un cluster où CoreDNS était à zéro replica. Ce qui
   mesure une présence lit la sortie STANDARD ; stderr sert aux messages
   d'erreur, pas à décider.

4. **Un namespace créé mais jamais supprimé.** Le lab suivant hérite alors d'un
   namespace qu'il ne connaît pas, ou attend un `Terminating` qui ne vient
   jamais. Le validateur l'attrape, mais seulement après avoir joué le lab ;
   ici, c'est instantané.

    pytest tests/test_pieges_du_depot.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"
REPERTOIRES = sorted(p.parent for p in LABS.glob("*/lab.yaml"))
IDS = [p.name for p in REPERTOIRES]

#: Un appel à la commande `ssh`, suivi de ses options courtes.
#: `(?!-)` écarte `ssh-keygen` et `ssh-copy-id` ; `\b` écarte `sshd` et
#: `ssh_config`, où le mot ne se termine pas après « ssh ».
APPEL_SSH = re.compile(r"\bssh\b(?!-)((?:\s+-[\w-]+(?:=\S+)?)*)")

#: `kubectl create namespace <nom>`, avec ou sans le `kubectl`.
CREE_NAMESPACE = re.compile(r"create\s+namespace\s+([a-z0-9-]+)")
#: `kubectl delete namespace <nom> [<nom>…]`, la forme du cleanup.
SUPPRIME_NAMESPACE = re.compile(r"delete\s+namespace\s+((?:[a-z0-9-]+\s+)*[a-z0-9-]+)")


def _lignes_de_code(fichier: Path) -> list[tuple[int, str]]:
    """Les lignes non commentées, avec leur numéro."""
    lignes = []
    for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), start=1):
        if ligne.strip().startswith("#"):
            continue
        lignes.append((numero, ligne))
    return lignes


def test_le_catalogue_est_parcouru() -> None:
    """Garde-fou : sans lui, un parcours cassé rendrait la suite verte à vide."""
    assert REPERTOIRES, "aucun lab trouvé sous labs/ : le parcours est cassé."


@pytest.mark.parametrize("lab", REPERTOIRES, ids=IDS)
def test_tout_ssh_d_une_solution_porte_l_option_n(lab: Path) -> None:
    solution = lab / "challenge" / "solution.sh"
    if not solution.is_file():
        pytest.skip("ce lab n'a pas de solution.sh")

    fautifs = [
        (numero, ligne.strip())
        for numero, ligne in _lignes_de_code(solution)
        for options in [APPEL_SSH.search(ligne)]
        if options and "-n" not in options.group(1).split()
    ]

    assert not fautifs, (
        f"{solution.relative_to(RACINE)} appelle ssh sans -n :\n"
        + "\n".join(f"  ligne {n} : {ligne}" for n, ligne in fautifs)
        + "\n\nLa solution est lue par `bash -s` depuis l'entrée standard. Sans "
        "-n, ssh avale le reste du script comme entrée : rien après lui ne "
        "s'exécute, et le script rend 0 sans avoir rien fait."
    )


@pytest.mark.parametrize("lab", REPERTOIRES, ids=IDS)
def test_tout_prepare_trace_dans_le_journal_du_noeud(lab: Path) -> None:
    fixtures = lab / "fixtures"
    if not fixtures.is_dir():
        pytest.skip("ce lab n'a pas de fixtures")

    sans_journal = [
        str(script.relative_to(RACINE))
        for script in sorted(fixtures.glob("*.sh"))
        if "/var/log/dsoxlab-" not in script.read_text(encoding="utf-8")
    ]

    assert not sans_journal, (
        f"Ces scripts de fixture ne tracent pas sur le nœud : {sans_journal}.\n"
        "dsoxlab ne rend que « non-zero return code » quand ils échouent. "
        "Reprenez l'en-tête d'un lab existant :\n"
        "  exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1\n"
        "  set -x"
    )


@pytest.mark.parametrize("lab", REPERTOIRES, ids=IDS)
def test_le_setup_installe_le_socle(lab: Path) -> None:
    setup = lab / "setup.yaml"
    assert setup.is_file(), f"{lab.name} n'a pas de setup.yaml."

    assert "kubeadm-cluster.yml" in setup.read_text(encoding="utf-8"), (
        f"{setup.relative_to(RACINE)} n'inclut pas shared/kubeadm-cluster.yml.\n"
        "Il n'y a aucun point d'accroche après le provisionnement : le cluster "
        "n'existe que parce que chaque lab l'installe. Ce lab tournera tant "
        "qu'un autre sera passé avant lui, et échouera seul sur un cluster neuf."
    )


@pytest.mark.parametrize("lab", REPERTOIRES, ids=IDS)
def test_tout_namespace_cree_est_supprime_au_nettoyage(lab: Path) -> None:
    crees: set[str] = set()
    for script in sorted((lab / "fixtures").glob("*.sh")) if (lab / "fixtures").is_dir() else []:
        crees |= set(CREE_NAMESPACE.findall(script.read_text(encoding="utf-8")))
    crees |= set(CREE_NAMESPACE.findall((lab / "setup.yaml").read_text(encoding="utf-8")))

    if not crees:
        pytest.skip("ce lab ne crée aucun namespace")

    cleanup = lab / "cleanup.yaml"
    assert cleanup.is_file(), f"{lab.name} crée {sorted(crees)} et n'a pas de cleanup.yaml."

    supprimes: set[str] = set()
    for groupe in SUPPRIME_NAMESPACE.findall(cleanup.read_text(encoding="utf-8")):
        supprimes |= set(groupe.split())

    oublies = sorted(crees - supprimes)
    assert not oublies, (
        f"{lab.name} crée le(s) namespace(s) {oublies} et son cleanup.yaml ne "
        "les supprime pas.\n"
        "Le lab suivant en hérite, ou attend un Terminating qui ne vient jamais. "
        "Le cluster, lui, reste en place : c'est le namespace qui part."
    )


@pytest.mark.parametrize("lab", REPERTOIRES, ids=IDS)
def test_aucun_test_ne_decide_sur_stdout_plus_stderr(lab: Path) -> None:
    """Le cinquième piège, payé le 2026-09-15.

    Concaténer les deux flux pour composer un MESSAGE est sain, et cinq labs le
    font. Décider sur le résultat ne l'est pas : le client SSH pollue stderr
    d'un avertissement sur les known_hosts, si bien qu'une assertion du type
    `assert (stdout + stderr).strip()` est vraie même quand la commande n'a
    rien rendu.

    Le lab DNS y a perdu un cycle de validation : son premier test passait avant
    le travail, alors que CoreDNS était à zéro replica. Seule la règle des deux
    sens l'a vu — un test qui ne sait pas échouer ne mesure rien.
    """
    fichier = lab / "challenge" / "tests" / "test_functional.py"
    if not fichier.is_file():
        pytest.skip("pas de test fonctionnel")

    fautives = []
    for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
        depouillee = ligne.strip()
        if not depouillee.startswith("assert"):
            continue
        # On ne vise QUE les assertions : la même expression dans un f-string
        # de message est légitime, et c'est le cas le plus fréquent.
        sans_message = depouillee.split(",", 1)[0]
        if "stdout" in sans_message and "stderr" in sans_message:
            fautives.append(f"ligne {numero} : {depouillee[:90]}")

    assert not fautives, (
        f"{lab.name} décide sur stdout + stderr :\n  "
        + "\n  ".join(fautives)
        + "\nLe client SSH écrit un avertissement sur stderr : la chaîne n'est "
        "jamais vide, et un test qui conclut « vide = absent » passe toujours. "
        "Lisez la sortie standard seule."
    )
