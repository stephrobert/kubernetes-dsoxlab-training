"""test_functional.py : cka-rbac-serviceaccount

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première veut le Pod en marche sous son identité ;
sans ServiceAccount, il n'existe pas. La deuxième lit le Role et le
RoleBinding et refuse tout droit en trop : un Role qui donnerait aussi
delete, ou secrets, passerait un candidat trop généreux. Les deux dernières
entrent dans le Pod et interrogent l'API avec le jeton projeté, ce qui est
la seule preuve que l'application, et pas l'administrateur, a ces droits :
lister doit répondre 200, tout le reste 403.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "app-team"
DEPLOYMENT = "inventaire"
SA = "pod-reader"
ROLE = "pod-reader-role"
BINDING = "pod-reader-binding"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
VERBES_LECTURE = {"get", "list", "watch"}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    """Le Pod d'inventaire, en marche. Le ReplicaSet réessaie toutes les
    quelques secondes après la création du ServiceAccount : on l'attend."""
    pod = None
    for _ in range(24):
        res = _kubectl(host, f"-n {NAMESPACE} get pods -l app={DEPLOYMENT} -o json")
        if res.rc == 0:
            vivants = [p for p in json.loads(res.stdout)["items"] if not p["metadata"].get("deletionTimestamp")]
            prets = [p for p in vivants if p["status"].get("phase") == "Running"
                     and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])]
            if prets:
                return prets[0]
            pod = vivants[0] if vivants else None
        time.sleep(5)
    assert pod is not None, (
        f"Aucun Pod de {DEPLOYMENT} dans {NAMESPACE} après deux minutes. Le ReplicaSet ne peut "
        f"pas en créer tant que le ServiceAccount {SA} n'existe pas : kubectl get events -n "
        f"{NAMESPACE} le dit."
    )
    pytest.fail(f"Le Pod de {DEPLOYMENT} existe mais n'est pas prêt : phase {pod['status'].get('phase')!r}.")


def _code_http(host, chemin: str, methode: str = "GET") -> str:
    """Interroge l'API depuis le Pod, avec son jeton, et rend le code HTTP."""
    # Le tout est passé à sh -c entre apostrophes : rien d'autre que des
    # guillemets à l'intérieur.
    commande = (
        "D=/var/run/secrets/kubernetes.io/serviceaccount; "
        f'curl -s -o /dev/null -w "%{{http_code}}" -X {methode} --cacert $D/ca.crt '
        f'-H "Authorization: Bearer $(cat $D/token)" https://kubernetes.default.svc{chemin}'
    )
    res = _kubectl(host, f"-n {NAMESPACE} exec deploy/{DEPLOYMENT} -- sh -c '{commande}'")
    assert res.rc == 0, f"kubectl exec dans {DEPLOYMENT} échoue : {res.stderr.strip()[:200]}"
    return res.stdout.strip()


# ----------------------------------------------------------------------
# 1. L'application tourne, sous son identité.
# ----------------------------------------------------------------------
def test_l_application_demarre_sous_son_identite(host):
    res = _kubectl(host, f"-n {NAMESPACE} get serviceaccount {SA} -o json")
    assert res.rc == 0, f"Aucun ServiceAccount {SA} dans {NAMESPACE} : c'est lui que le Deployment attend."
    pod = _pod(host)
    assert pod["spec"].get("serviceAccountName") == SA, (
        f"Le Pod tourne sous {pod['spec'].get('serviceAccountName')!r} au lieu de {SA} : le "
        "Deployment a été modifié pour contourner le problème, pas résolu."
    )


# ----------------------------------------------------------------------
# 2. Le Role accorde la lecture des Pods, et rien de plus.
# ----------------------------------------------------------------------
def test_le_role_accorde_la_lecture_et_rien_de_plus(host):
    res = _kubectl(host, f"-n {NAMESPACE} get role {ROLE} -o json")
    assert res.rc == 0, f"Aucun Role {ROLE} dans {NAMESPACE}."
    verbes_pods: set[str] = set()
    autres: list[str] = []
    for regle in json.loads(res.stdout).get("rules") or []:
        ressources = set(regle.get("resources") or [])
        verbes = set(regle.get("verbs") or [])
        if "pods" in ressources or "*" in ressources:
            verbes_pods |= verbes
        autres += sorted(r for r in ressources if r not in ("pods",))
    assert verbes_pods >= VERBES_LECTURE, (
        f"Le Role donne {sorted(verbes_pods)} sur les Pods, il manque {sorted(VERBES_LECTURE - verbes_pods)}."
    )
    en_trop = verbes_pods - VERBES_LECTURE
    assert not en_trop, (
        f"Le Role donne aussi {sorted(en_trop)} sur les Pods. Lire, c'est get, list et watch ; "
        "un verbe de plus est un droit que l'application n'a pas demandé."
    )
    assert not autres, (
        f"Le Role touche à d'autres ressources que les Pods : {autres}. Le moindre privilège "
        "s'arrête à ce dont l'application a besoin."
    )
    res = _kubectl(host, f"-n {NAMESPACE} get rolebinding {BINDING} -o json")
    assert res.rc == 0, f"Aucun RoleBinding {BINDING} dans {NAMESPACE}."
    rb = json.loads(res.stdout)
    assert rb["roleRef"].get("kind") == "Role" and rb["roleRef"].get("name") == ROLE, (
        f"Le RoleBinding vise {rb['roleRef'].get('kind')}/{rb['roleRef'].get('name')} au lieu de Role/{ROLE}."
    )
    sujets = [(s.get("kind"), s.get("namespace"), s.get("name")) for s in rb.get("subjects") or []]
    assert ("ServiceAccount", NAMESPACE, SA) in sujets, (
        f"Le RoleBinding ne nomme pas le ServiceAccount {NAMESPACE}/{SA} (sujets : {sujets}). Un Pod "
        "s'identifie par son ServiceAccount, avec kind ServiceAccount et le namespace, pas par un User."
    )


# ----------------------------------------------------------------------
# 3. Depuis le Pod, lister les Pods passe.
# ----------------------------------------------------------------------
def test_depuis_le_pod_lister_les_pods_passe(host):
    _pod(host)
    code = _code_http(host, f"/api/v1/namespaces/{NAMESPACE}/pods")
    assert code == "200", (
        f"Depuis le Pod, GET /api/v1/namespaces/{NAMESPACE}/pods répond {code} au lieu de 200. "
        "Le jeton projeté identifie le ServiceAccount ; s'il est refusé, le RoleBinding ne le "
        "nomme pas, ou le Role ne donne pas list."
    )


# ----------------------------------------------------------------------
# 4. La preuve : tout le reste est refusé.
# ----------------------------------------------------------------------
def test_depuis_le_pod_tout_le_reste_est_refuse(host):
    pod = _pod(host)
    refus = {
        "supprimer un Pod d'app-team": _code_http(host, f"/api/v1/namespaces/{NAMESPACE}/pods/{pod['metadata']['name']}", "DELETE"),
        "lire les Secrets d'app-team": _code_http(host, f"/api/v1/namespaces/{NAMESPACE}/secrets"),
        "lister les Pods de default": _code_http(host, "/api/v1/namespaces/default/pods"),
    }
    passes = {k: v for k, v in refus.items() if v != "403"}
    assert not passes, (
        f"Ces requêtes devraient répondre 403 et répondent : {passes}. Le ServiceAccount a plus "
        "de droits que la consigne : un Role trop large, un ClusterRoleBinding, ou un rôle "
        "existant réutilisé. L'application ne doit pouvoir que lire les Pods de son namespace."
    )
