"""test_functional.py : k8s-changer-de-contexte

Quatre tests, un par état demandé : le contexte actif, le namespace par défaut
de ce contexte, une commande lancée sans préciser ni contexte ni namespace, dont
le résultat doit atterrir au bon endroit, et les droits du kubeconfig, qui ne
doit être accessible qu'à son propriétaire.

La préparation a déjà réuni les deux clusters dans ~/.kube/config. Le contexte
recette est reconnu à ce qu'il désigne : son cluster doit avoir l'adresse du
cluster « lab », lue dans le kubeconfig d'administration de ce cluster. Renommer
kind-boutique en recette ne suffit donc pas.

La ConfigMap preuve est le contrôle : créée sans -n ni --context, elle va là où
le kubeconfig envoie. Elle doit exister dans kube-system du cluster lab, et nulle
part dans le cluster boutique.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

ADMIN_RECETTE = "/etc/kind/lab.kubeconfig"
ADMIN_BOUTIQUE = "/etc/kind/boutique.kubeconfig"
CONTEXTE = "recette"
NAMESPACE = "kube-system"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


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


def _preuves(host, admin: str) -> list[str]:
    """Les namespaces où une ConfigMap preuve existe, dans le cluster donné."""
    res = host.run(f"sudo kubectl --kubeconfig {admin} get configmap -A --field-selector metadata.name=preuve -o json")
    if res.rc != 0:
        return []
    return sorted(i["metadata"]["namespace"] for i in json.loads(res.stdout).get("items", []))


# ----------------------------------------------------------------------
# 1. Le contexte actif est recette, et il vise le cluster lab.
# ----------------------------------------------------------------------
def test_le_contexte_actif_est_recette(host, principal):
    actif = principal.get("current-context", "")
    attendu = _serveur(_kubeconfig(host, ADMIN_RECETTE), "kind-lab")
    vise = _serveur(principal, _contexte(principal, actif).get("cluster", ""))
    assert actif == CONTEXTE and attendu and vise == attendu, message(
        en=f"The active context is {actif!r}, which points at {vise or 'no server'}. Expected {CONTEXTE!r}, "
        f"pointing at the recette cluster ({attendu}). The switch is written in current-context, for every "
        "terminal.",
        fr=f"Le contexte actif est {actif!r}, qui vise {vise or 'aucun serveur'}. Attendu {CONTEXTE!r}, qui vise "
        f"le cluster de recette ({attendu}). La bascule s'écrit dans current-context, pour tous les terminaux.",
    )


# ----------------------------------------------------------------------
# 2. Le namespace par défaut du contexte recette.
# ----------------------------------------------------------------------
def test_le_namespace_par_defaut_de_recette_est_kube_system(principal):
    namespace = _contexte(principal, CONTEXTE).get("namespace", "")
    assert namespace == NAMESPACE, message(
        en=f"The default namespace of {CONTEXTE} is {namespace or 'not set (default)'!r}, expected {NAMESPACE!r}. "
        "kubectl does not check that the name exists: read it back after setting it.",
        fr=f"Le namespace par défaut de {CONTEXTE} est {namespace or 'non réglé (default)'!r}, attendu "
        f"{NAMESPACE!r}. kubectl ne vérifie pas que le nom existe : relisez-le après l'avoir réglé.",
    )


# ----------------------------------------------------------------------
# 3. La preuve, créée sans -n ni --context, est au bon endroit.
# ----------------------------------------------------------------------
def test_la_preuve_est_dans_kube_system_du_cluster_recette(host):
    recette = _preuves(host, ADMIN_RECETTE)
    boutique = _preuves(host, ADMIN_BOUTIQUE)
    assert recette == [NAMESPACE] and not boutique, message(
        en=f"The ConfigMap preuve exists in the namespace(s) {recette or 'none'} of the recette cluster, and "
        f"{boutique or 'none'} of the boutique cluster. Expected {NAMESPACE} of the recette cluster only: created "
        "with neither -n nor --context, it lands where the active context and its default namespace send it.",
        fr=f"La ConfigMap preuve existe dans le(s) namespace(s) {recette or 'aucun'} du cluster de recette, et "
        f"{boutique or 'aucun'} du cluster boutique. Attendu {NAMESPACE} du cluster de recette seulement : créée "
        "sans -n ni --context, elle atterrit là où l'envoient le contexte actif et son namespace par défaut.",
    )


# ----------------------------------------------------------------------
# 4. Le kubeconfig n'est accessible qu'à son propriétaire.
# ----------------------------------------------------------------------
def test_le_kubeconfig_n_est_accessible_qu_a_son_proprietaire(host):
    fichier = host.file(f"{_maison(host)}/.kube/config")
    utilisateur = host.check_output('echo "${SUDO_USER:-ansible}"').strip()
    mode = fichier.mode if fichier.exists else None
    assert fichier.exists and mode == 0o600 and fichier.user == utilisateur, message(
        en=f"~/.kube/config has mode {oct(mode) if mode is not None else 'absent'} and belongs to "
        f"{fichier.user if fichier.exists else 'nobody'}. Expected 600, owned by {utilisateur}: the file holds a "
        "client key, which nobody else may read, and kubectl itself must still be able to read and write it.",
        fr=f"~/.kube/config a les droits {oct(mode) if mode is not None else 'absent'} et appartient à "
        f"{fichier.user if fichier.exists else 'personne'}. Attendu 600, à {utilisateur} : le fichier contient une "
        "clé client, que personne d'autre ne doit lire, et kubectl doit toujours pouvoir le lire et l'écrire.",
    )
