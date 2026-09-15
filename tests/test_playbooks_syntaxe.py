"""Tout `setup.yaml` / `cleanup.yaml` doit être chargeable par Ansible.

Incident à l'origine de ce module, relevé dans le catalogue Linux jumeau. Un
commentaire français ajouté **dans** un bloc `ansible.builtin.shell` a suffi à
casser un playbook : l'apostrophe de « n'empêche » déséquilibre le découpage des
arguments, et Ansible refuse de charger la tâche avec « failed at splitting
arguments, either an unbalanced jinja2 block or quotes ».

Le fichier restait un YAML parfaitement valide. `yaml.safe_load` passait,
`dsoxlab validate-structure` passait, et le défaut ne se voyait qu'à
l'exécution, sous la forme d'un `dsoxlab run` qui échouait en `rc=4` sans jouer
une seule tâche. Vérifier la forme ne prouve pas que ça s'exécute : seul
`--syntax-check` charge réellement les tâches.

Un commentaire explicatif se met donc **au-dessus** de la tâche, en YAML, pas à
l'intérieur du bloc shell.

Ce que ce contrôle NE voit pas, et c'est important de le savoir : les tâches
incluses dynamiquement. `shared/kubeadm-cluster.yml` arrive par
`include_tasks`, qu'Ansible ne résout qu'à l'exécution. Le socle est donc
vérifié à part, en le chargeant comme un playbook autonome.

    pytest tests/test_playbooks_syntaxe.py -v
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
PLAYBOOKS = sorted(
    p for p in (RACINE / "labs").rglob("*.yaml") if p.name in {"setup.yaml", "cleanup.yaml"}
)
ANSIBLE = shutil.which("ansible-playbook")


def _charge(fichier: Path, *, comme_taches: bool = False) -> subprocess.CompletedProcess:
    """Demande à Ansible de charger le fichier, sans rien exécuter."""
    assert ANSIBLE is not None
    if comme_taches:
        # Un fichier de tâches n'est pas un playbook : il n'a ni `hosts` ni
        # `tasks`, c'est une liste de tâches nue. On l'enveloppe le temps du
        # contrôle, sinon Ansible refuse le fichier pour la mauvaise raison.
        enveloppe = fichier.parent / f".syntaxe-{fichier.stem}.yml"
        enveloppe.write_text(
            "- name: Controle de syntaxe\n"
            "  hosts: localhost\n"
            "  gather_facts: false\n"
            "  tasks:\n"
            f"    - ansible.builtin.include_tasks: {fichier.name}\n",
            encoding="utf-8",
        )
        try:
            return subprocess.run(
                [ANSIBLE, "--syntax-check", "-i", "localhost,", str(enveloppe)],
                capture_output=True,
                text=True,
                cwd=RACINE,
                check=False,
            )
        finally:
            enveloppe.unlink(missing_ok=True)

    return subprocess.run(
        [ANSIBLE, "--syntax-check", "-i", "localhost,", str(fichier)],
        capture_output=True,
        text=True,
        cwd=RACINE,
        # C'est le code de retour qu'on veut juger, pas une exception : un
        # playbook qui ne se charge pas doit produire un échec lisible.
        check=False,
    )


def test_le_catalogue_a_bien_des_playbooks() -> None:
    """Garde-fou du garde-fou : une liste vide ferait passer le test pour rien."""
    assert len(PLAYBOOKS) >= 2 * len(list((RACINE / "labs").glob("*/lab.yaml"))), (
        f"seulement {len(PLAYBOOKS)} playbook(s) découvert(s) pour "
        f"{len(list((RACINE / 'labs').glob('*/lab.yaml')))} lab(s) : chaque lab doit "
        "porter un setup.yaml ET un cleanup.yaml."
    )


@pytest.mark.skipif(ANSIBLE is None, reason="ansible-playbook absent du PATH")
@pytest.mark.parametrize("playbook", PLAYBOOKS, ids=lambda p: str(p.relative_to(RACINE)))
def test_le_playbook_se_charge(playbook: Path) -> None:
    resultat = _charge(playbook)

    assert resultat.returncode == 0, (
        f"{playbook.relative_to(RACINE)} ne se charge pas :\n"
        f"{resultat.stdout.strip()}\n{resultat.stderr.strip()}\n\n"
        "Un commentaire explicatif se met au-dessus de la tâche, en YAML, jamais "
        "à l'intérieur d'un bloc shell : une apostrophe y casse le découpage des "
        "arguments sans que le YAML cesse d'être valide."
    )


@pytest.mark.skipif(ANSIBLE is None, reason="ansible-playbook absent du PATH")
@pytest.mark.parametrize(
    "taches",
    sorted((RACINE / "shared").glob("*.yml")),
    ids=lambda p: str(p.relative_to(RACINE)),
)
def test_le_socle_se_charge(taches: Path) -> None:
    """Le socle arrive par `include_tasks` : aucun setup.yaml ne le charge au
    contrôle de syntaxe, il faut donc le charger pour lui-même."""
    resultat = _charge(taches, comme_taches=True)

    assert resultat.returncode == 0, (
        f"{taches.relative_to(RACINE)} ne se charge pas :\n"
        f"{resultat.stdout.strip()}\n{resultat.stderr.strip()}\n\n"
        "Ce fichier est inclus par TOUS les labs : une faute ici les casse tous "
        "à la fois, et le message parlera du lab, pas du socle."
    )
