"""test_functional.py : k8s-changer-de-contexte

Ces tests lisent les fichiers kubeconfig de l'apprenant et leurs droits : la
fusion, le renommage, la bascule et le namespace par défaut sont tous écrits
dans ~/.kube/config. Un test vérifie un seul état demandé par l'énoncé.

Le contexte recette est reconnu à ce qu'il désigne : son cluster doit avoir
l'adresse du cluster reçu, lue dans le kubeconfig d'administration de ce
cluster. Le contexte kind-boutique doit avoir survécu à la fusion : copier le
fichier reçu par-dessus le sien n'est pas fusionner.
"""

from __future__ import annotations

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

RECU = "/etc/kind/lab.kubeconfig"
CONTEXTE = "recette"
DEPART = "kind-boutique"
NAMESPACE = "kube-system"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _utilisateur(host) -> str:
    return host.check_output('echo "${SUDO_USER:-ansible}"').strip()


def _kubeconfig(host, chemin: str) -> dict:
    fichier = host.file(chemin)
    if not fichier.exists:
        return {}
    try:
        return yaml.safe_load(fichier.content_string) or {}
    except yaml.YAMLError:
        return {}


def _contexte(conf: dict, nom: str) -> dict:
    for c in conf.get("contexts") or []:
        if c.get("name") == nom:
            return c.get("context") or {}
    return {}


def _serveur(conf: dict, cluster: str) -> str:
    for c in conf.get("clusters") or []:
        if c.get("name") == cluster:
            return (c.get("cluster") or {}).get("server", "")
    return ""


@pytest.fixture(scope="module")
def principal(host) -> dict:
    return _kubeconfig(host, f"{_maison(host)}/.kube/config")


# ----------------------------------------------------------------------
# 1. Le kubeconfig reçu, rangé et protégé.
# ----------------------------------------------------------------------
def test_le_kubeconfig_recu_est_range_et_protege(host):
    maison = _maison(host)
    range_ = host.file(f"{maison}/.kube/configs/recette.yaml")
    assert range_.exists, message(
        en="No ~/.kube/configs/recette.yaml. A received kubeconfig does not stay in "
        "~/Downloads: it is stored in ~/.kube/configs/. Reread the section of the lesson on "
        "merging a received kubeconfig.",
        fr="Aucun ~/.kube/configs/recette.yaml. Un kubeconfig reçu ne reste pas dans "
        "~/Downloads : il se range dans ~/.kube/configs/. Relisez la section de la leçon sur "
        "la fusion d'un kubeconfig reçu.",
    )
    assert range_.mode & 0o077 == 0 and range_.user == _utilisateur(host), message(
        en=f"~/.kube/configs/recette.yaml has mode {oct(range_.mode)} and belongs to "
        f"{range_.user}: it holds a client key, it must be readable by its owner only (600).",
        fr=f"~/.kube/configs/recette.yaml a les droits {oct(range_.mode)} et appartient à "
        f"{range_.user} : il contient une clé client, il ne doit être lisible que par son "
        "propriétaire (600).",
    )
    assert not host.file(f"{maison}/Downloads/kubeconfig-recette.yaml").exists, message(
        en="~/Downloads/kubeconfig-recette.yaml is still there: a kubeconfig left in "
        "~/Downloads is a credential lying around. Move it, do not copy it.",
        fr="~/Downloads/kubeconfig-recette.yaml est toujours là : un kubeconfig laissé dans "
        "~/Downloads est un accès qui traîne. Déplacez-le, ne le copiez pas.",
    )


# ----------------------------------------------------------------------
# 2. Le contexte recette fusionné, sans écraser kind-boutique.
# ----------------------------------------------------------------------
def test_le_contexte_recette_est_fusionne_sans_ecraser_kind_boutique(host, principal):
    recette = _contexte(principal, CONTEXTE)
    assert recette, message(
        en=f"~/.kube/config has no context named {CONTEXTE}. After the merge, the received "
        "context is named kind-recette: rename it.",
        fr=f"~/.kube/config n'a aucun contexte nommé {CONTEXTE}. Après la fusion, le contexte "
        "reçu s'appelle kind-recette : renommez-le.",
    )
    attendu = _serveur(_kubeconfig(host, RECU), "kind-lab")
    vise = _serveur(principal, recette.get("cluster", ""))
    assert attendu and vise == attendu, message(
        en=f"The context {CONTEXTE} points at {vise or 'no server'}, which is not the cluster of "
        "the received kubeconfig.",
        fr=f"Le contexte {CONTEXTE} vise {vise or 'aucun serveur'}, qui n'est pas le cluster du "
        "kubeconfig reçu.",
    )
    assert _contexte(principal, DEPART), message(
        en=f"The context {DEPART} has disappeared from ~/.kube/config: the received file was "
        "copied over yours instead of being merged. Merge with KUBECONFIG listing both files "
        "and kubectl config view --flatten, after a backup.",
        fr=f"Le contexte {DEPART} a disparu de ~/.kube/config : le fichier reçu a été copié "
        "par-dessus le vôtre au lieu d'être fusionné. Fusionnez avec KUBECONFIG listant les "
        "deux fichiers et kubectl config view --flatten, après une sauvegarde.",
    )


# ----------------------------------------------------------------------
# 3. Le contexte actif.
# ----------------------------------------------------------------------
def test_le_contexte_actif_est_recette(principal):
    actif = principal.get("current-context", "")
    assert actif == CONTEXTE, message(
        en=f"The active context is {actif!r}, expected {CONTEXTE!r}. The switch is written in "
        "current-context, for every terminal.",
        fr=f"Le contexte actif est {actif!r}, attendu {CONTEXTE!r}. La bascule s'écrit dans "
        "current-context, pour tous les terminaux.",
    )


# ----------------------------------------------------------------------
# 4. Le namespace par défaut du contexte recette.
# ----------------------------------------------------------------------
def test_le_namespace_par_defaut_de_recette_est_kube_system(principal):
    namespace = _contexte(principal, CONTEXTE).get("namespace", "")
    assert namespace == NAMESPACE, message(
        en=f"The default namespace of {CONTEXTE} is {namespace or 'not set (default)'!r}, "
        f"expected {NAMESPACE!r}. kubectl does not check that the name exists: read it back "
        "after setting it.",
        fr=f"Le namespace par défaut de {CONTEXTE} est {namespace or 'non réglé (default)'!r}, "
        f"attendu {NAMESPACE!r}. kubectl ne vérifie pas que le nom existe : relisez-le après "
        "l'avoir réglé.",
    )


# ----------------------------------------------------------------------
# 5. Le kubeconfig principal protégé.
# ----------------------------------------------------------------------
def test_le_kubeconfig_principal_n_est_lisible_que_par_son_proprietaire(host):
    fichier = host.file(f"{_maison(host)}/.kube/config")
    assert fichier.exists and fichier.mode & 0o077 == 0, message(
        en=f"~/.kube/config has mode {oct(fichier.mode) if fichier.exists else 'absent'}: "
        "a file written by a redirection takes the default mode, often readable by all. It "
        "must be readable by its owner only (600).",
        fr=f"~/.kube/config a les droits {oct(fichier.mode) if fichier.exists else 'absent'} : "
        "un fichier écrit par une redirection prend les droits par défaut, souvent lisibles "
        "par tous. Il ne doit être lisible que par son propriétaire (600).",
    )
