"""test_functional.py : cka-placer-un-pod-pending

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Quatre
applications du namespace placement restent en Pending, chacune pour une cause
différente de la leçon « Diagnostiquer un Pod Pending » : des ressources
impossibles, un nodeSelector que rien ne satisfait, une taint non tolérée, un
PVC qu'aucun volume ne lie.

Un test par application, plus le diagnostic. Aucun n'est vrai avant le
travail : le setup laisse les quatre Pods en Pending et ne pose aucun
ConfigMap de diagnostic. Chaque test vérifie AUSSI ce que la correction ne
devait pas sacrifier : l'exigence NVMe du cache, la réserve du nœud de batch,
la classe du volume des archives. Supprimer la contrainte ferait démarrer le
Pod, et ce n'est pas la réparation demandée.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "placement"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD_NVME = "k8s-w2.lab"
NOEUD_BATCH = "k8s-w1.lab"
TAINT_BATCH = {"key": "equipe", "value": "batch", "effect": "NoSchedule"}
CLASSE_ARCHIVES = "lente"
CAUSES = {"calcul": "ressources", "cache": "selecteur", "batch": "taint", "archives": "volume"}


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, commande: str) -> dict:
    res = host.run(f"sudo {KUBECTL} {commande} -o json")
    assert res.rc == 0, message(
        en=f"`kubectl {commande}` failed: {res.stderr.strip()}",
        fr=f"`kubectl {commande}` a échoué : {res.stderr.strip()}",
    )
    return json.loads(res.stdout)


def _pod_pret(host, app: str, delai: int = 60) -> dict:
    """Le Pod de l'application, prêt, ou un échec qui dit où il en est.

    Une correction juste met quelques secondes à produire un Pod prêt (tirage
    d'image, liaison du volume) : on attend, avec un budget borné, plutôt que
    de recaler un travail correct sur une photo prise trop tôt.
    """
    fin = time.time() + delai
    pods: list[dict] = []
    while True:
        pods = _json(host, f"-n {NAMESPACE} get pods -l app={app}").get("items", [])
        prets = [
            p for p in pods
            if p["status"].get("phase") == "Running"
            and all(c.get("ready") for c in p["status"].get("containerStatuses") or [{}])
        ]
        if prets or time.time() > fin:
            break
        time.sleep(3)
    if not prets:
        etats = ", ".join(f"{p['metadata']['name']}={p['status'].get('phase')}" for p in pods) or "aucun Pod"
        pytest.fail(message(
            en=f"Application {app} has no ready Pod ({etats}). The FailedScheduling event of "
            f"`kubectl describe pod -n {NAMESPACE} -l app={app}` says why the scheduler finds no node.",
            fr=f"L'application {app} n'a aucun Pod prêt ({etats}). L'événement FailedScheduling de "
            f"`kubectl describe pod -n {NAMESPACE} -l app={app}` dit pourquoi le scheduler ne trouve "
            "aucun nœud.",
        ))
    return prets[0]


def _cpu_en_millicoeurs(valeur: str) -> int:
    return int(valeur[:-1]) if valeur.endswith("m") else int(float(valeur) * 1000)


# ----------------------------------------------------------------------
# 1. Le diagnostic nomme la cause de chaque blocage.
# ----------------------------------------------------------------------
def test_le_diagnostic_nomme_chaque_cause(host):
    res = host.run(f"sudo {KUBECTL} -n {NAMESPACE} get configmap diagnostic -o json")
    assert res.rc == 0, message(
        en=f"No ConfigMap diagnostic in namespace {NAMESPACE}. Write one key per application "
        "(calcul, cache, batch, archives), each with its cause: ressources, selecteur, taint or volume.",
        fr=f"Aucun ConfigMap diagnostic dans le namespace {NAMESPACE}. Écrivez une clé par application "
        "(calcul, cache, batch, archives), chacune avec sa cause : ressources, selecteur, taint ou volume.",
    )
    donnees = json.loads(res.stdout).get("data") or {}
    lues = {app: (donnees.get(app) or "").strip().lower() for app in CAUSES}
    fausses = {app: lue for app, lue in lues.items() if lue != CAUSES[app]}
    assert not fausses, message(
        en=f"The diagnostic names a wrong cause, or none, for: {fausses}. Each FailedScheduling "
        "message lists why every node was rejected: the cause is the reason that rejects the nodes "
        "this application could use, not the background noise.",
        fr=f"Le diagnostic nomme une cause fausse, ou aucune, pour : {fausses}. Chaque message "
        "FailedScheduling dit pourquoi chaque nœud a été écarté : la cause est la raison qui écarte les "
        "nœuds que cette application pourrait utiliser, pas le bruit de fond.",
    )


# ----------------------------------------------------------------------
# 2. calcul : des requests réalistes.
# ----------------------------------------------------------------------
def test_calcul_demande_une_part_realiste(host):
    pod = _pod_pret(host, "calcul")
    requete = ((pod["spec"]["containers"][0].get("resources") or {}).get("requests") or {}).get("cpu")
    assert requete, message(
        en="calcul runs, but its container no longer requests any CPU: without requests the scheduler "
        "places it blindly. Lower the request to what a node can give, do not remove it.",
        fr="calcul tourne, mais son conteneur ne demande plus aucun CPU : sans requests, le scheduler le "
        "place à l'aveugle. Réduisez la demande à ce qu'un nœud peut donner, ne la retirez pas.",
    )
    noeuds = _json(host, "get nodes")["items"]
    plus_grand = max(_cpu_en_millicoeurs(n["status"]["allocatable"]["cpu"]) for n in noeuds)
    assert _cpu_en_millicoeurs(requete) <= plus_grand, message(
        en=f"calcul requests {requete} CPU, more than any node can allocate ({plus_grand}m).",
        fr=f"calcul demande {requete} CPU, plus qu'aucun nœud ne peut allouer ({plus_grand}m).",
    )


# ----------------------------------------------------------------------
# 3. cache : l'exigence NVMe est tenue, par le bon nœud.
# ----------------------------------------------------------------------
def test_cache_tourne_sur_le_noeud_nvme(host):
    deploy = _json(host, f"-n {NAMESPACE} get deployment cache")
    selecteur = deploy["spec"]["template"]["spec"].get("nodeSelector") or {}
    assert selecteur.get("disk") == "ssd-nvme", message(
        en="The cache Deployment no longer asks for disk=ssd-nvme. The team needs the NVMe disk: "
        "removing the constraint starts the Pod on a slow disk, it does not fix the placement.",
        fr="Le Deployment cache ne demande plus disk=ssd-nvme. L'équipe a besoin du disque NVMe : retirer "
        "la contrainte démarre le Pod sur un disque lent, cela ne répare pas le placement.",
    )
    etiquetes = sorted(
        n["metadata"]["name"] for n in _json(host, "get nodes")["items"]
        if n["metadata"].get("labels", {}).get("disk") == "ssd-nvme"
    )
    assert etiquetes == [NOEUD_NVME], message(
        en=f"Nodes labelled disk=ssd-nvme: {etiquetes or 'none'}. Only {NOEUD_NVME} has the NVMe disk: "
        "a label is a promise the scheduler believes, it must only be on the node that keeps it.",
        fr=f"Nœuds étiquetés disk=ssd-nvme : {etiquetes or 'aucun'}. Seul {NOEUD_NVME} porte le disque "
        "NVMe : une étiquette est une promesse que le scheduler croit, elle ne va que sur le nœud qui la tient.",
    )
    pod = _pod_pret(host, "cache")
    assert pod["spec"].get("nodeName") == NOEUD_NVME, message(
        en=f"cache runs on {pod['spec'].get('nodeName')}, not on {NOEUD_NVME}.",
        fr=f"cache tourne sur {pod['spec'].get('nodeName')}, pas sur {NOEUD_NVME}.",
    )


# ----------------------------------------------------------------------
# 4. batch : toléré sur son nœud réservé, sans lever la réserve.
# ----------------------------------------------------------------------
def test_batch_tolere_la_reserve_sans_la_lever(host):
    noeud = _json(host, f"get node {NOEUD_BATCH}")
    taints = noeud["spec"].get("taints") or []
    assert any(all(t.get(k) == v for k, v in TAINT_BATCH.items()) for t in taints), message(
        en=f"The taint equipe=batch:NoSchedule is gone from {NOEUD_BATCH}. It reserves that node for the "
        "batch team: removing it lets any Pod in. The batch Pod must tolerate it.",
        fr=f"La taint equipe=batch:NoSchedule a disparu de {NOEUD_BATCH}. Elle réserve ce nœud à l'équipe "
        "batch : la retirer y laisse entrer n'importe quel Pod. C'est le Pod de batch qui doit la tolérer.",
    )
    pod = _pod_pret(host, "batch")
    assert pod["spec"].get("nodeName") == NOEUD_BATCH, message(
        en=f"batch runs on {pod['spec'].get('nodeName')}, not on its reserved node {NOEUD_BATCH}.",
        fr=f"batch tourne sur {pod['spec'].get('nodeName')}, pas sur son nœud réservé {NOEUD_BATCH}.",
    )


# ----------------------------------------------------------------------
# 5. archives : le volume se lie, dans sa classe, et s'écrit.
# ----------------------------------------------------------------------
def test_archives_ecrit_sur_son_volume(host):
    pvc = _json(host, f"-n {NAMESPACE} get pvc archives-data")
    assert pvc["spec"].get("storageClassName") == CLASSE_ARCHIVES, message(
        en=f"The PVC archives-data asks for class {pvc['spec'].get('storageClassName')}, not "
        f"{CLASSE_ARCHIVES}. Keep the claim as it is: the missing piece is the volume, not the claim.",
        fr=f"Le PVC archives-data demande la classe {pvc['spec'].get('storageClassName')}, pas "
        f"{CLASSE_ARCHIVES}. Gardez la demande telle quelle : ce qui manque est le volume, pas la demande.",
    )
    assert pvc.get("status", {}).get("phase") == "Bound", message(
        en=f"The PVC archives-data is {pvc.get('status', {}).get('phase')}: no PersistentVolume of class "
        f"{CLASSE_ARCHIVES} with enough capacity and the right access mode matches it.",
        fr=f"Le PVC archives-data est {pvc.get('status', {}).get('phase')} : aucun PersistentVolume de "
        f"classe {CLASSE_ARCHIVES}, assez grand et au bon mode d'accès, ne lui correspond.",
    )
    pod = _pod_pret(host, "archives")
    nom = pod["metadata"]["name"]
    res = host.run(
        f"sudo {KUBECTL} -n {NAMESPACE} exec {nom} -- sh -c "
        "'echo dsoxlab > /data/.dsoxlab-ecriture && cat /data/.dsoxlab-ecriture && rm /data/.dsoxlab-ecriture'"
    )
    assert res.rc == 0 and "dsoxlab" in res.stdout, message(
        en=f"archives runs, but writing to /data fails: {res.stderr.strip()}",
        fr=f"archives tourne, mais l'écriture dans /data échoue : {res.stderr.strip()}",
    )
