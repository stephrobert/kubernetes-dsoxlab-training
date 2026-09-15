"""test_functional.py : ckad-rbac-role-rolebinding

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. La première lit le Role et le RoleBinding ; les deux
autres interrogent l'API EN TANT QUE dev-user, et c'est cela qui prouve :
un Role bien écrit sans RoleBinding, ou un RoleBinding vers un mauvais nom,
donneraient un manifeste plausible et une utilisatrice sans droits. Chaque
test qui vérifie un droit accordé vérifie aussi un droit refusé, sans quoi
un ClusterRoleBinding cluster-admin passerait le lab.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
ROLE = "pod-reader"
BINDING = "read-pods-binding"
UTILISATRICE = "dev-user"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _peut(host, verbe: str, ressource: str, namespace: str) -> bool:
    res = _kubectl(host, f"auth can-i {verbe} {ressource} -n {namespace} --as {UTILISATRICE}")
    return res.stdout.strip().startswith("yes")


# ----------------------------------------------------------------------
# 1. Le Role et le RoleBinding existent, et se répondent.
# ----------------------------------------------------------------------
def test_le_role_et_le_binding_se_repondent(host):
    res = _kubectl(host, f"-n {NAMESPACE} get role {ROLE} -o json")
    assert res.rc == 0, f"Aucun Role {ROLE} dans {NAMESPACE}. Un Role est limité à un namespace : c'est ici qu'il se crée."
    role = json.loads(res.stdout)
    ressources = {r for regle in role.get("rules") or [] for r in regle.get("resources") or []}
    assert "pods" in ressources, f"Le Role {ROLE} ne porte pas sur les pods : resources {sorted(ressources)}."
    assert "pods/log" in ressources, (
        f"Le Role {ROLE} ne porte pas sur pods/log : les logs sont une sous-ressource, "
        "à nommer à part dans resources."
    )
    res = _kubectl(host, f"-n {NAMESPACE} get rolebinding {BINDING} -o json")
    assert res.rc == 0, f"Aucun RoleBinding {BINDING} dans {NAMESPACE}. Sans lui, un Role ne donne rien à personne."
    binding = json.loads(res.stdout)
    ref = binding.get("roleRef") or {}
    assert ref.get("kind") == "Role" and ref.get("name") == ROLE, (
        f"{BINDING} référence {ref.get('kind')} {ref.get('name')!r} et non le Role {ROLE}."
    )
    sujets = {(s.get("kind"), s.get("name")) for s in binding.get("subjects") or []}
    assert ("User", UTILISATRICE) in sujets, (
        f"{BINDING} ne lie pas l'utilisatrice {UTILISATRICE} : sujets {sorted(sujets)}. "
        "Le sujet est de kind User, avec son nom exact."
    )


# ----------------------------------------------------------------------
# 2. dev-user lit les Pods et leurs logs, et ne peut pas créer.
# ----------------------------------------------------------------------
def test_dev_user_lit_sans_pouvoir_ecrire(host):
    assert _peut(host, "list", "pods", NAMESPACE), (
        f"{UTILISATRICE} ne peut pas lister les Pods de {NAMESPACE}. Role et "
        "RoleBinding existent peut-être, mais l'API dit non : vérifiez le nom du "
        "sujet et les verbs du Role, list en fait partie."
    )
    assert _peut(host, "get", "pods/log", NAMESPACE), (
        f"{UTILISATRICE} ne peut pas lire les logs. Le droit sur pods ne couvre "
        "pas pods/log : c'est une sous-ressource, à ajouter au Role."
    )
    logs = _kubectl(host, f"--as {UTILISATRICE} -n {NAMESPACE} logs journal --tail=1")
    assert logs.rc == 0 and "journal" in logs.stdout, (
        f"En tant que {UTILISATRICE}, kubectl logs journal échoue : {logs.stderr.strip()[:150]}"
    )
    assert not _peut(host, "create", "pods", NAMESPACE), (
        f"{UTILISATRICE} peut CRÉER des Pods dans {NAMESPACE} : c'est trop. Lire, "
        "c'est get, list, watch ; rien d'autre."
    )


# ----------------------------------------------------------------------
# 3. Le droit ne déborde pas du namespace ni des Pods.
# ----------------------------------------------------------------------
def test_le_droit_reste_dans_le_namespace(host):
    assert _peut(host, "list", "pods", NAMESPACE), (
        f"{UTILISATRICE} ne peut toujours pas lister les Pods de {NAMESPACE} : le test précédent dit pourquoi."
    )
    assert not _peut(host, "list", "pods", "default"), (
        f"{UTILISATRICE} peut lister les Pods de default : le droit déborde du "
        "namespace. Un ClusterRoleBinding, ou un binding dans le mauvais "
        "namespace, donne plus que demandé."
    )
    assert not _peut(host, "list", "secrets", NAMESPACE), (
        f"{UTILISATRICE} peut lister les Secrets de {NAMESPACE} : le Role couvre plus "
        "que les Pods et leurs logs."
    )
