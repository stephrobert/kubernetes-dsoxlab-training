"""test_functional.py : k8s-challenge-maintenir-un-noeud

Sept états, un par test, dans l'ordre de la fiche du challenge. Tous lisent le
cluster kubeadm depuis k8s-cp.lab ; le dernier lit aussi le dépôt git de
l'équipe, au commit courant.

L'évacuation se prouve sans dépendre du placement, comme dans
cka-node-drain-cordon : le Pod sans contrôleur outil-diag a disparu, au moins
un Pod du catalogue est né après l'heure de pose, et AUCUN Pod né avant elle ne
tourne encore sur le worker. La montée de version vide aussi les nœuds, si bien
que des Pods récents peuvent être revenus sur le worker : ils ne comptent pas
contre l'évacuation.

Les sept échouent sur l'état de départ : aucun budget, outil-diag et des Pods
d'origine sur le worker, aucune trace, cluster en 1.36.4, MAX_CONNEXIONS à 50
dans le cluster comme dans le dépôt.
"""

from __future__ import annotations

import base64
import json
import math
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS = "maintenance"
WORKER = "k8s-w1.lab"
DEPLOYMENT = "catalogue"
REPLICAS = 4
PDB = "catalogue-pdb"
ORPHELIN = "outil-diag"
TRACE = "drain-evidence"
CONFIG = "catalogue-config"
CLE = "MAX_CONNEXIONS"
NOUVELLE_VALEUR = "200"
ANNOTATION = "lab.dsoxlab/pose-le"
VERSION_CIBLE = "v1.37.0"
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
SONDE = "sonde-placement"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _api(host) -> None:
    res = host.run(f"{KUBECTL} get --raw /readyz --request-timeout=20s")
    assert res.rc == 0, message(
        en=f"The API server does not answer: {res.stderr.strip()[:200]}",
        fr=f"L'API server ne répond pas : {res.stderr.strip()[:200]}",
    )


def _pret(objet: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (objet.get("status") or {}).get("conditions") or [])


def _pods_du_catalogue(host) -> list[dict]:
    pods = (_json(host, f"-n {NS} get pods -l app={DEPLOYMENT}") or {}).get("items") or []
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")]


def _evacuation_a_eu_lieu(host) -> None:
    _api(host)
    dep = _json(host, f"-n {NS} get deployment {DEPLOYMENT}")
    assert dep is not None, message(
        en=f"Deployment {DEPLOYMENT} no longer exists in {NS}: maintenance moves the application, "
        "it does not remove it.",
        fr=f"Le Deployment {DEPLOYMENT} n'existe plus dans {NS} : une maintenance déplace "
        "l'application, elle ne la retire pas.",
    )
    pose = (dep["metadata"].get("annotations") or {}).get(ANNOTATION)
    assert pose, message(
        en=f"Deployment {DEPLOYMENT} no longer carries the {ANNOTATION} annotation set by the setup.",
        fr=f"Le Deployment {DEPLOYMENT} n'a plus l'annotation {ANNOTATION} posée par le setup.",
    )
    pods = _pods_du_catalogue(host)
    recrees = [p["metadata"]["name"] for p in pods if p["metadata"]["creationTimestamp"] > pose]
    assert recrees, message(
        en=f"No Pod of {DEPLOYMENT} has been recreated since the challenge started: no eviction took "
        "place.",
        fr=f"Aucun Pod de {DEPLOYMENT} n'a été recréé depuis le début du challenge : aucune éviction "
        "n'a eu lieu.",
    )
    anciens = [p["metadata"]["name"] for p in pods
               if p["metadata"]["creationTimestamp"] <= pose and p["spec"].get("nodeName") == WORKER]
    assert not anciens, message(
        en=f"Pods of {DEPLOYMENT} from before the maintenance still run on {WORKER}: {anciens}. The "
        "worker was not emptied.",
        fr=f"Des Pods de {DEPLOYMENT} d'avant la maintenance tournent encore sur {WORKER} : "
        f"{anciens}. Le worker n'a pas été vidé.",
    )


def _garantis(pdb: dict, replicas: int) -> int | None:
    """Le nombre de Pods que le budget garde disponibles, pour ce nombre de réplicas."""
    spec = pdb.get("spec") or {}
    if spec.get("minAvailable") is not None:
        v = spec["minAvailable"]
        return math.ceil(replicas * int(v[:-1]) / 100) if isinstance(v, str) and v.endswith("%") else int(v)
    if spec.get("maxUnavailable") is not None:
        v = spec["maxUnavailable"]
        manque = math.ceil(replicas * int(v[:-1]) / 100) if isinstance(v, str) and v.endswith("%") else int(v)
        return replicas - manque
    return None


# ----------------------------------------------------------------------
# 1. Un budget nommé garantit au moins deux Pods du catalogue.
# ----------------------------------------------------------------------
def test_le_budget_garantit_deux_pods_du_catalogue(host):
    _api(host)
    pdb = _json(host, f"-n {NS} get pdb {PDB}")
    assert pdb is not None, message(
        en=f"No PodDisruptionBudget {PDB} in {NS}. Without a budget, a drain evicts every Pod of "
        "the node at once.",
        fr=f"Aucun PodDisruptionBudget {PDB} dans {NS}. Sans budget, un drain évince tous les Pods "
        "du nœud d'un coup.",
    )
    garantis = _garantis(pdb, REPLICAS)
    assert garantis is not None and 2 <= garantis < REPLICAS, message(
        en=f"With {REPLICAS} replicas, the budget keeps {garantis} Pod(s) available. Expected at "
        "least two, and fewer than all of them, otherwise no drain can ever go through.",
        fr=f"Avec {REPLICAS} réplicas, le budget garde {garantis} Pod(s) disponible(s). Attendu au "
        "moins deux, et moins que tous, sinon aucun drain ne passera jamais.",
    )
    attendus = 0
    for _ in range(12):
        attendus = (pdb.get("status") or {}).get("expectedPods", 0)
        if attendus == REPLICAS:
            break
        time.sleep(5)
        pdb = _json(host, f"-n {NS} get pdb {PDB}") or pdb
    assert attendus == REPLICAS, message(
        en=f"The budget counts {attendus} expected Pod(s) instead of {REPLICAS}: its selector does not "
        f"match the Pods of {DEPLOYMENT}. A budget that targets nothing protects nothing.",
        fr=f"Le budget compte {attendus} Pod(s) attendu(s) au lieu de {REPLICAS} : son selector ne "
        f"matche pas les Pods de {DEPLOYMENT}. Un budget qui ne vise rien ne protège rien.",
    )


# ----------------------------------------------------------------------
# 2. Le worker a été évacué : Pods recréés, Pod isolé parti, DaemonSet resté.
# ----------------------------------------------------------------------
def test_le_worker_a_ete_evacue(host):
    _evacuation_a_eu_lieu(host)
    pods = _pods_du_catalogue(host)
    assert len(pods) == REPLICAS, message(
        en=f"{len(pods)} Pod(s) of {DEPLOYMENT} instead of {REPLICAS}: the replicas were not to be "
        "touched.",
        fr=f"{len(pods)} Pod(s) de {DEPLOYMENT} au lieu de {REPLICAS} : il ne fallait pas toucher aux "
        "réplicas.",
    )
    orphelin = _json(host, f"-n {NS} get pod {ORPHELIN}")
    assert orphelin is None or orphelin["metadata"].get("deletionTimestamp"), message(
        en=f"Pod {ORPHELIN} is still on the worker. It has no controller, so drain refuses it by "
        "default: the instructions say it may disappear.",
        fr=f"Le Pod {ORPHELIN} est toujours sur le worker. Il n'a aucun contrôleur, le drain le refuse "
        "donc par défaut : la consigne dit qu'il peut disparaître.",
    )
    calico = [p for p in (_json(host, "-n calico-system get pods -l k8s-app=calico-node") or {}).get("items") or []
              if p["spec"].get("nodeName") == WORKER and not p["metadata"].get("deletionTimestamp")]
    assert calico, message(
        en=f"No calico-node Pod on {WORKER}: the network DaemonSet was removed. A drain ignores "
        "DaemonSets, it does not make them disappear.",
        fr=f"Aucun Pod calico-node sur {WORKER} : le DaemonSet du réseau a été retiré. Un drain ignore "
        "les DaemonSets, il ne les fait pas disparaître.",
    )


# ----------------------------------------------------------------------
# 3. Le worker est remis en service et accepte de nouveau des Pods.
# ----------------------------------------------------------------------
def test_le_worker_est_remis_en_service(host):
    _evacuation_a_eu_lieu(host)
    noeud = _json(host, f"get node {WORKER}") or {}
    assert noeud and not noeud["spec"].get("unschedulable", False), message(
        en=f"{WORKER} is still out of scheduling (SchedulingDisabled): maintenance is over, it goes "
        "back into service.",
        fr=f"{WORKER} est toujours hors du scheduling (SchedulingDisabled) : la maintenance est "
        "finie, il revient en service.",
    )
    assert _pret(noeud), message(
        en=f"{WORKER} is not Ready.",
        fr=f"{WORKER} n'est pas Ready.",
    )
    sonde = base64.b64encode(json.dumps({
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": SONDE, "namespace": NS},
        "spec": {"nodeSelector": {"kubernetes.io/hostname": WORKER}, "restartPolicy": "Never",
                 "containers": [{"name": "sonde", "image": BUSYBOX, "command": ["sleep", "60"]}]},
    }).encode()).decode()
    host.run(f"{KUBECTL} -n {NS} delete pod {SONDE} --ignore-not-found --wait=true")
    try:
        cree = host.run(f"echo {sonde} | base64 -d | {KUBECTL} apply -f -")
        assert cree.rc == 0, message(
            en=f"The grader cannot create its probe Pod: {cree.stderr.strip()[:200]}",
            fr=f"Le correcteur ne peut pas créer son Pod sonde : {cree.stderr.strip()[:200]}",
        )
        attente = host.run(f"{KUBECTL} -n {NS} wait --for=condition=Ready pod/{SONDE} --timeout=90s")
        assert attente.rc == 0, message(
            en=f"A Pod the scheduler must place on {WORKER} does not start there within 90 s: the "
            "worker does not accept new Pods.",
            fr=f"Un Pod que le scheduler doit placer sur {WORKER} n'y démarre pas en 90 s : le worker "
            "n'accepte pas de nouveaux Pods.",
        )
    finally:
        host.run(f"{KUBECTL} -n {NS} delete pod {SONDE} --ignore-not-found --wait=false")


# ----------------------------------------------------------------------
# 4. La trace nomme le nœud vidé et porte le statut completed.
# ----------------------------------------------------------------------
def test_la_trace_nomme_le_noeud_vide(host):
    _api(host)
    trace = _json(host, f"-n {NS} get configmap {TRACE}")
    assert trace is not None, message(
        en=f"No ConfigMap {TRACE} in {NS}.",
        fr=f"Aucun ConfigMap {TRACE} dans {NS}.",
    )
    data = trace.get("data") or {}
    assert data.get("drained-node") == WORKER and data.get("status") == "completed", message(
        en=f"{TRACE} carries drained-node={data.get('drained-node')!r} and status={data.get('status')!r}; "
        f"expected {WORKER!r} and 'completed'.",
        fr=f"{TRACE} porte drained-node={data.get('drained-node')!r} et status={data.get('status')!r} ; "
        f"attendu {WORKER!r} et 'completed'.",
    )


# ----------------------------------------------------------------------
# 5. L'API server annonce 1.37.0.
# ----------------------------------------------------------------------
def test_l_api_server_annonce_1_37_0(host):
    res = host.run(f"{KUBECTL} version -o json --request-timeout=30s")
    assert res.rc == 0, message(
        en=f"Cannot read the version: the API server does not answer. {res.stderr.strip()[:200]}",
        fr=f"Impossible de lire la version : l'API server ne répond pas. {res.stderr.strip()[:200]}",
    )
    serveur = (json.loads(res.stdout).get("serverVersion") or {}).get("gitVersion", "")
    assert serveur.split("+")[0] == VERSION_CIBLE, message(
        en=f"The API server reports {serveur!r}, not {VERSION_CIBLE}. The cluster started from 1.36.4: "
        "the control plane goes up first, with a kubeadm already at the target version.",
        fr=f"L'API server annonce {serveur!r}, et non {VERSION_CIBLE}. Le cluster est parti de 1.36.4 : "
        "le plan de contrôle monte d'abord, avec un kubeadm déjà à la version visée.",
    )


# ----------------------------------------------------------------------
# 6. Chaque nœud en 1.37.0, aucun inordonnançable, le catalogue entier prêt.
# ----------------------------------------------------------------------
def test_chaque_noeud_en_1_37_0_ordonnancable_et_le_catalogue_tient(host):
    _api(host)
    noeuds = (_json(host, "get nodes") or {}).get("items") or []
    assert len(noeuds) >= 2, message(
        en=f"The cluster has {len(noeuds)} node(s), expected the control plane and the worker.",
        fr=f"Le cluster a {len(noeuds)} nœud(s), attendu le plan de contrôle et le worker.",
    )
    en_retard = {n["metadata"]["name"]: n["status"]["nodeInfo"]["kubeletVersion"] for n in noeuds
                 if n["status"]["nodeInfo"]["kubeletVersion"].split("+")[0] != VERSION_CIBLE}
    assert not en_retard, message(
        en=f"These nodes report another version: {en_retard}. Upgrading the control plane does not "
        "upgrade the kubelets: each node gets its package and restarts its kubelet.",
        fr=f"Ces nœuds annoncent une autre version : {en_retard}. Monter le plan de contrôle ne monte "
        "pas les kubelets : chaque nœud reçoit son paquet et redémarre son kubelet.",
    )
    vides = [n["metadata"]["name"] for n in noeuds if n["spec"].get("unschedulable")]
    assert not vides, message(
        en=f"These nodes were left unschedulable: {vides}. A node drained for the upgrade goes back "
        "into service afterwards.",
        fr=f"Ces nœuds sont restés inordonnançables : {vides}. Un nœud vidé pour la montée revient en "
        "service ensuite.",
    )
    pas_prets = [n["metadata"]["name"] for n in noeuds if not _pret(n)]
    assert not pas_prets, message(
        en=f"These nodes are not Ready: {pas_prets}. `journalctl -u kubelet` on the node says why.",
        fr=f"Ces nœuds ne sont pas Ready : {pas_prets}. `journalctl -u kubelet` sur le nœud dit "
        "pourquoi.",
    )
    pretes = 0
    for _ in range(18):
        dep = _json(host, f"-n {NS} get deployment {DEPLOYMENT}") or {}
        pretes = (dep.get("status") or {}).get("readyReplicas") or 0
        if pretes == REPLICAS:
            break
        time.sleep(5)
    assert pretes == REPLICAS, message(
        en=f"{DEPLOYMENT} has {pretes} ready replica(s) out of {REPLICAS}. The budget keeps two up during "
        "the work; at the end, the application is whole again.",
        fr=f"{DEPLOYMENT} a {pretes} réplica(s) prêt(s) sur {REPLICAS}. Le budget en garde deux pendant "
        "les travaux ; à la fin, l'application est de nouveau entière.",
    )


# ----------------------------------------------------------------------
# 7. Le champ modifié en direct porte la même valeur dans le dépôt.
# ----------------------------------------------------------------------
def test_le_champ_modifie_en_direct_est_reporte_dans_le_depot(host):
    _api(host)
    vivant = ((_json(host, f"-n {NS} get configmap {CONFIG}") or {}).get("data") or {}).get(CLE)
    assert vivant == NOUVELLE_VALEUR, message(
        en=f"In the cluster, {CLE} of {CONFIG} is {vivant!r}, expected {NOUVELLE_VALEUR!r}.",
        fr=f"Dans le cluster, {CLE} de {CONFIG} vaut {vivant!r}, attendu {NOUVELLE_VALEUR!r}.",
    )
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    res = host.run(f"git -c safe.directory='*' -C {maison}/maintenance show HEAD:{CONFIG}.yaml")
    assert res.rc == 0, message(
        en=f"~/maintenance holds no committed {CONFIG}.yaml: {res.stderr.strip()[:200]}",
        fr=f"~/maintenance ne porte aucun {CONFIG}.yaml commité : {res.stderr.strip()[:200]}",
    )
    try:
        depot = ((yaml.safe_load(res.stdout) or {}).get("data") or {}).get(CLE)
    except yaml.YAMLError:
        depot = None
    assert str(depot) == NOUVELLE_VALEUR, message(
        en=f"The last commit of ~/maintenance gives {CLE} = {depot!r}, while the cluster runs with "
        f"{vivant!r}. A change made live is carried into the versioned manifest, otherwise the next "
        "apply silently undoes it.",
        fr=f"Le dernier commit de ~/maintenance donne {CLE} = {depot!r}, alors que le cluster tourne "
        f"avec {vivant!r}. Une modification faite en direct se reporte dans le manifeste versionné, "
        "sinon le prochain apply la défait sans bruit.",
    )
