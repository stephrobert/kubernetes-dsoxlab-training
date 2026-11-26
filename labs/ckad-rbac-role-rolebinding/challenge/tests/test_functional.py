"""test_functional.py : ckad-rbac-role-rolebinding

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Cinq affirmations. Les deux premières lisent le Role puis le RoleBinding ; les
trois autres interrogent l'API EN TANT QUE dev-user, et c'est cela qui prouve :
un Role bien écrit sans RoleBinding, ou un RoleBinding vers un mauvais nom,
donneraient un manifeste plausible et une utilisatrice sans droits. Chaque
test qui vérifie un droit accordé vérifie aussi un droit refusé, sans quoi
un ClusterRoleBinding cluster-admin passerait le lab.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

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
# 1. Le Role porte sur les Pods et leurs logs.
# ----------------------------------------------------------------------
def test_le_role_couvre_les_pods_et_leurs_logs(host):
    res = _kubectl(host, f"-n {NAMESPACE} get role {ROLE} -o json")
    assert res.rc == 0, message(
        en=f"No Role {ROLE} in {NAMESPACE}. A Role is scoped to a namespace: this is where it is created.",
        fr=f"Aucun Role {ROLE} dans {NAMESPACE}. Un Role est limité à un namespace : c'est ici qu'il se crée.",
    )
    role = json.loads(res.stdout)
    ressources = {r for regle in role.get("rules") or [] for r in regle.get("resources") or []}
    assert "pods" in ressources, message(
        en=f"Role {ROLE} does not cover pods: resources {sorted(ressources)}.",
        fr=f"Le Role {ROLE} ne porte pas sur les pods : resources {sorted(ressources)}.",
    )
    assert "pods/log" in ressources, message(
        en=f"Role {ROLE} does not cover pods/log: logs are a subresource, "
        "to be named separately under resources.",
        fr=f"Le Role {ROLE} ne porte pas sur pods/log : les logs sont une sous-ressource, "
        "à nommer à part dans resources.",
    )


# ----------------------------------------------------------------------
# 2. Le RoleBinding donne ce Role à dev-user.
# ----------------------------------------------------------------------
def test_le_binding_donne_le_role_a_dev_user(host):
    res = _kubectl(host, f"-n {NAMESPACE} get rolebinding {BINDING} -o json")
    assert res.rc == 0, message(
        en=f"No RoleBinding {BINDING} in {NAMESPACE}. Without it, a Role grants nothing to anyone.",
        fr=f"Aucun RoleBinding {BINDING} dans {NAMESPACE}. Sans lui, un Role ne donne rien à personne.",
    )
    binding = json.loads(res.stdout)
    ref = binding.get("roleRef") or {}
    assert ref.get("kind") == "Role" and ref.get("name") == ROLE, message(
        en=f"{BINDING} references {ref.get('kind')} {ref.get('name')!r} and not Role {ROLE}.",
        fr=f"{BINDING} référence {ref.get('kind')} {ref.get('name')!r} et non le Role {ROLE}.",
    )
    sujets = {(s.get("kind"), s.get("name")) for s in binding.get("subjects") or []}
    assert ("User", UTILISATRICE) in sujets, message(
        en=f"{BINDING} does not bind user {UTILISATRICE}: subjects {sorted(sujets)}. "
        "The subject is of kind User, with its exact name.",
        fr=f"{BINDING} ne lie pas l'utilisatrice {UTILISATRICE} : sujets {sorted(sujets)}. "
        "Le sujet est de kind User, avec son nom exact.",
    )


# ----------------------------------------------------------------------
# 3 et 4. dev-user lit les Pods, puis leurs logs, et ne peut pas créer.
# ----------------------------------------------------------------------
def _ne_peut_pas_creer(host) -> None:
    """Vrai avant le travail : il accompagne chaque droit accordé."""
    assert not _peut(host, "create", "pods", NAMESPACE), message(
        en=f"{UTILISATRICE} can CREATE Pods in {NAMESPACE}: that is too much. Reading "
        "means get, list, watch; nothing else.",
        fr=f"{UTILISATRICE} peut CRÉER des Pods dans {NAMESPACE} : c'est trop. Lire, "
        "c'est get, list, watch ; rien d'autre.",
    )


def test_dev_user_liste_les_pods_sans_pouvoir_en_creer(host):
    assert _peut(host, "list", "pods", NAMESPACE), message(
        en=f"{UTILISATRICE} cannot list the Pods of {NAMESPACE}. Role and "
        "RoleBinding may exist, but the API says no: check the subject's "
        "name and the Role's verbs, list being one of them.",
        fr=f"{UTILISATRICE} ne peut pas lister les Pods de {NAMESPACE}. Role et "
        "RoleBinding existent peut-être, mais l'API dit non : vérifiez le nom du "
        "sujet et les verbs du Role, list en fait partie.",
    )
    _ne_peut_pas_creer(host)


def test_dev_user_lit_les_logs_sans_pouvoir_creer(host):
    assert _peut(host, "get", "pods/log", NAMESPACE), message(
        en=f"{UTILISATRICE} cannot read the logs. The right on pods does not cover "
        "pods/log: that is a subresource, to be added to the Role.",
        fr=f"{UTILISATRICE} ne peut pas lire les logs. Le droit sur pods ne couvre "
        "pas pods/log : c'est une sous-ressource, à ajouter au Role.",
    )
    logs = _kubectl(host, f"--as {UTILISATRICE} -n {NAMESPACE} logs journal --tail=1")
    assert logs.rc == 0 and "journal" in logs.stdout, message(
        en=f"As {UTILISATRICE}, kubectl logs journal fails: {logs.stderr.strip()[:150]}",
        fr=f"En tant que {UTILISATRICE}, kubectl logs journal échoue : {logs.stderr.strip()[:150]}",
    )
    _ne_peut_pas_creer(host)


# ----------------------------------------------------------------------
# 5. Le droit ne déborde pas du namespace ni des Pods.
# ----------------------------------------------------------------------
def test_le_droit_reste_dans_le_namespace(host):
    assert _peut(host, "list", "pods", NAMESPACE), message(
        en=f"{UTILISATRICE} still cannot list the Pods of {NAMESPACE}: the previous test says why.",
        fr=f"{UTILISATRICE} ne peut toujours pas lister les Pods de {NAMESPACE} : le test précédent dit pourquoi.",
    )
    assert not _peut(host, "list", "pods", "default"), message(
        en=f"{UTILISATRICE} can list the Pods of default: the right spills out of the "
        "namespace. A ClusterRoleBinding, or a binding in the wrong "
        "namespace, grants more than was asked.",
        fr=f"{UTILISATRICE} peut lister les Pods de default : le droit déborde du "
        "namespace. Un ClusterRoleBinding, ou un binding dans le mauvais "
        "namespace, donne plus que demandé.",
    )
    assert not _peut(host, "list", "secrets", NAMESPACE), message(
        en=f"{UTILISATRICE} can list the Secrets of {NAMESPACE}: the Role covers more "
        "than the Pods and their logs.",
        fr=f"{UTILISATRICE} peut lister les Secrets de {NAMESPACE} : le Role couvre plus "
        "que les Pods et leurs logs.",
    )
