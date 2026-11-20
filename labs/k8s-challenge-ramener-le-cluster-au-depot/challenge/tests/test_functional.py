"""test_functional.py : k8s-challenge-ramener-le-cluster-au-depot

Ces tests lisent l'état du cluster et le dépôt git ~/annuaire, jamais les
commandes tapées.

La préparation applique le dépôt, puis fait trois modifications en direct :
la montée à N réplicas (N tiré au sort, la seule que l'équipe garde), un
CACHE_TTL changé dans la ConfigMap, et une variable DEBUG ajoutée par
`kubectl set env`. Cette dernière n'est pas dans la dernière configuration
appliquée : `kubectl diff` ne la montre pas, et `kubectl apply` ne la retire
pas. Un diff vide ne suffit donc pas à réussir.

Deux tests sont bloquants, parce qu'ils portent le cœur du geste : le dépôt
et le cluster disent la même chose (`kubectl diff` vide), et la montée en
réplicas voulue est reportée et commitée dans le dépôt.

Tous échouent avant le travail : le diff montre les réplicas et le TTL, le
dépôt n'a que son commit initial, DEBUG est posée.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

NS = "annuaire"
DEPLOIEMENT, CONFIG = "annuaire-api", "annuaire-config"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MEMOIRE = "/var/lib/dsoxlab/challenge-ramener-le-cluster-au-depot.json"
RIEN_COMMITE = "rien n'a été commité depuis le départ"
OBJET_D_ORIGINE = "est l'objet d'origine"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def depot(host) -> str:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    return f"{maison}/annuaire"


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _git(host, depot: str, args: str):
    return host.run(f"git -c safe.directory='*' -C {depot} {args}")


# ----------------------------------------------------------------------
# 1. Le dépôt et le cluster disent la même chose. BLOQUANT.
# ----------------------------------------------------------------------
def test_kubectl_diff_est_vide_sur_le_depot(host, depot):
    res = host.run(f"{ADMIN} diff -f {depot}")
    lignes = [li for li in res.stdout.splitlines() if li.startswith(("-  ", "+  "))]
    assert res.rc == 0, message(
        en=f"`kubectl diff -f ~/annuaire` still finds a gap (code {res.rc}): {lignes[:6] or res.stderr.strip()[:200]}",
        fr=f"`kubectl diff -f ~/annuaire` trouve encore un écart (code {res.rc}) : "
        f"{lignes[:6] or res.stderr.strip()[:200]}",
    )


# ----------------------------------------------------------------------
# 2. La montée en réplicas voulue est reportée et commitée. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_montee_en_replicas_est_reportee_et_commitee(host, depot, memoire):
    voulu = memoire["replicas"]
    vivant = ((_json(host, f"-n {NS} get deployment {DEPLOIEMENT}") or {}).get("spec") or {}).get("replicas")
    res = _git(host, depot, "show HEAD:deployment.yaml")
    try:
        commite = ((yaml.safe_load(res.stdout) or {}).get("spec") or {}).get("replicas") if res.rc == 0 else None
    except yaml.YAMLError:
        commite = None
    tete = _git(host, depot, "rev-parse HEAD").stdout.strip()
    propre = _git(host, depot, "status --porcelain").stdout.strip() == ""
    assert vivant == voulu and commite == voulu and tete != memoire["commit"] and propre, message(
        en=f"The cluster runs {vivant!r} replica(s), the last commit of ~/annuaire declares {commite!r}, "
        f"{'a new commit exists' if tete != memoire['commit'] else 'nothing was committed since the start'}, "
        f"and the working tree {'is clean' if propre else 'holds uncommitted changes'}. Expected the replica "
        "count raised during the night, kept in the cluster and committed in the repository.",
        fr=f"Le cluster tourne avec {vivant!r} réplica(s), le dernier commit de ~/annuaire en déclare "
        f"{commite!r}, {'un nouveau commit existe' if tete != memoire['commit'] else RIEN_COMMITE}, "
        f"et l'arbre de travail {'est propre' if propre else 'porte des changements non commités'}. Attendu : "
        "le nombre de réplicas monté pendant la nuit, gardé dans le cluster et commité dans le dépôt.",
    )


# ----------------------------------------------------------------------
# 3. Les autres modifications faites en direct ont disparu.
# ----------------------------------------------------------------------
def test_les_modifications_en_direct_non_voulues_ont_disparu(host, memoire):
    ttl = ((_json(host, f"-n {NS} get configmap {CONFIG}") or {}).get("data") or {}).get("CACHE_TTL")
    dep = _json(host, f"-n {NS} get deployment {DEPLOIEMENT}") or {}
    conteneurs = (((dep.get("spec") or {}).get("template") or {}).get("spec") or {}).get("containers") or []
    variables = sorted(e["name"] for c in conteneurs for e in c.get("env") or [])
    assert ttl == memoire["ttl_depot"] and not variables, message(
        en=f"CACHE_TTL is {ttl!r} in the cluster (the repository says {memoire['ttl_depot']!r}), and the "
        f"containers carry the variables {variables or 'none'} outside the ConfigMap. Every change made live, "
        "except the replicas, must be gone.",
        fr=f"CACHE_TTL vaut {ttl!r} dans le cluster (le dépôt dit {memoire['ttl_depot']!r}), et les conteneurs "
        f"portent les variables {variables or 'aucune'} hors de la ConfigMap. Toute modification faite en "
        "direct, hors les réplicas, doit avoir disparu.",
    )


# ----------------------------------------------------------------------
# 4. Les objets ont été modifiés, pas recréés.
# ----------------------------------------------------------------------
def test_les_objets_n_ont_pas_ete_recrees(host, memoire, depot):
    # Le test ne compte qu'une fois le dépôt et le cluster alignés : au
    # départ, rien n'est recréé, mais rien n'est fait non plus.
    aligne = host.run(f"{ADMIN} diff -f {depot}").rc == 0
    assert aligne, message(
        en="The cluster is not yet brought back to the repository: kubectl diff still finds a gap.",
        fr="Le cluster n'est pas encore ramené au dépôt : kubectl diff trouve encore un écart.",
    )
    uid_dep = ((_json(host, f"-n {NS} get deployment {DEPLOIEMENT}") or {}).get("metadata") or {}).get("uid")
    uid_cm = ((_json(host, f"-n {NS} get configmap {CONFIG}") or {}).get("metadata") or {}).get("uid")
    assert uid_dep == memoire["uid_deployment"] and uid_cm == memoire["uid_configmap"], message(
        en=f"{DEPLOIEMENT} {'is the original object' if uid_dep == memoire['uid_deployment'] else 'was deleted or recreated'}, "
        f"{CONFIG} {'is the original object' if uid_cm == memoire['uid_configmap'] else 'was deleted or recreated'}. "
        "Bring the live objects back to the repository without deleting them.",
        fr=f"{DEPLOIEMENT} {OBJET_D_ORIGINE if uid_dep == memoire['uid_deployment'] else 'a été supprimé ou recréé'}, "
        f"{CONFIG} {OBJET_D_ORIGINE if uid_cm == memoire['uid_configmap'] else 'a été supprimé ou recréé'}. "
        "Ramenez les objets vivants au dépôt sans les supprimer.",
    )


# ----------------------------------------------------------------------
# 5. L'application tourne avec tous ses réplicas, sur la configuration du dépôt.
# ----------------------------------------------------------------------
def test_l_application_tourne_sur_la_configuration_du_depot(host, memoire):
    dep = _json(host, f"-n {NS} get deployment {DEPLOIEMENT}") or {}
    statut = dep.get("status") or {}
    pods = (_json(host, f"-n {NS} get pods -l app={DEPLOIEMENT}") or {}).get("items", [])
    ttls = set()
    for pod in pods:
        if pod["status"].get("phase") != "Running" or pod["metadata"].get("deletionTimestamp"):
            continue
        res = host.run(f"{ADMIN} -n {NS} exec {pod['metadata']['name']} -- printenv CACHE_TTL")
        ttls.add(res.stdout.strip())
    assert statut.get("availableReplicas") == memoire["replicas"] and ttls == {memoire["ttl_depot"]}, message(
        en=f"{DEPLOIEMENT} has {statut.get('availableReplicas', 0)} replica(s) available, and its Pods read "
        f"CACHE_TTL = {sorted(ttls) or 'nothing'}. Expected {memoire['replicas']} replicas, all started on the "
        "configuration of the repository.",
        fr=f"{DEPLOIEMENT} a {statut.get('availableReplicas', 0)} réplica(s) disponible(s), et ses Pods lisent "
        f"CACHE_TTL = {sorted(ttls) or 'rien'}. Attendu {memoire['replicas']} réplicas, tous démarrés sur la "
        "configuration du dépôt.",
    )
