"""test_functional.py : cka-node-affinity

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le label du nœud. La deuxième lit les
affinités déclarées par storage-app, l'obligatoire et la préférée, avec
leurs opérateurs, valeurs et poids. La troisième lit le nœud réel de ses
trois Pods : la contrainte obligatoire ne laisse qu'un nœud possible, et
c'est ce qui se mesure. La quatrième veut gpu-app en marche sur un nœud
étiqueté accelerator=gpu, avec l'affinité qui l'a fait attendre, et sans
avoir été recréé après la pose du label.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
WORKER = "k8s-w1.lab"
DEPLOYMENT = "storage-app"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str) -> dict:
    res = _kubectl(host, args + " -o json")
    assert res.rc == 0, message(
        en=f"kubectl {args} failed: {res.stderr.strip()[:200]}",
        fr=f"kubectl {args} échoue : {res.stderr.strip()[:200]}",
    )
    return json.loads(res.stdout)


def _expressions(termes: list[dict]) -> list[tuple]:
    """Aplati des nodeSelectorTerms ou une preference en (clé, opérateur, valeurs)."""
    out = []
    for t in termes:
        for e in t.get("matchExpressions") or []:
            out.append((e.get("key"), e.get("operator"), sorted(e.get("values") or [])))
    return out


# ----------------------------------------------------------------------
# 1. Le nœud à disques rapides est étiqueté.
# ----------------------------------------------------------------------
def test_le_worker_est_etiquete_ssd(host):
    labels = _json(host, f"get node {WORKER}")["metadata"].get("labels") or {}
    assert labels.get("disktype") == "ssd", message(
        en=f"{WORKER} has disktype={labels.get('disktype')!r}, expected ssd: kubectl label nodes.",
        fr=f"{WORKER} a disktype={labels.get('disktype')!r}, attendu ssd : kubectl label nodes.",
    )


# ----------------------------------------------------------------------
# 2. storage-app déclare l'obligatoire et le préféré.
# ----------------------------------------------------------------------
def test_storage_app_declare_les_deux_affinites(host):
    res = _kubectl(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT} -o json")
    assert res.rc == 0, message(
        en=f"No Deployment {DEPLOYMENT} in {NAMESPACE}.",
        fr=f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.",
    )
    d = json.loads(res.stdout)
    assert d["spec"].get("replicas") == 3, message(
        en=f"{DEPLOYMENT} asks for {d['spec'].get('replicas')} replica(s) instead of 3.",
        fr=f"{DEPLOYMENT} demande {d['spec'].get('replicas')} replica(s) au lieu de 3.",
    )
    affinite = ((d["spec"]["template"]["spec"].get("affinity") or {}).get("nodeAffinity") or {})
    obligatoire = _expressions((affinite.get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or [])
    assert ("disktype", "In", ["nvme", "ssd"]) in obligatoire, message(
        en=f"The required affinity of {DEPLOYMENT} is {obligatoire}, expected disktype In [ssd, nvme]. "
        "That is requiredDuringSchedulingIgnoredDuringExecution, with the In operator and both values.",
        fr=f"L'affinité obligatoire de {DEPLOYMENT} est {obligatoire}, attendu disktype In [ssd, nvme]. "
        "C'est requiredDuringSchedulingIgnoredDuringExecution, avec l'opérateur In et les deux valeurs.",
    )
    preferes = affinite.get("preferredDuringSchedulingIgnoredDuringExecution") or []
    bons = [
        p for p in preferes
        if p.get("weight") == 80 and ("storage-tier", "In", ["fast"]) in _expressions([p.get("preference") or {}])
    ]
    assert bons, message(
        en=f"No preference of weight 80 on storage-tier In [fast] (preferences: "
        f"{[(p.get('weight'), _expressions([p.get('preference') or {}])) for p in preferes]}). "
        "That is preferredDuringSchedulingIgnoredDuringExecution, a list of weight and preference.",
        fr=f"Aucune préférence de poids 80 sur storage-tier In [fast] (préférences : "
        f"{[(p.get('weight'), _expressions([p.get('preference') or {}])) for p in preferes]}). "
        "C'est preferredDuringSchedulingIgnoredDuringExecution, une liste de weight et preference.",
    )


# ----------------------------------------------------------------------
# 3. Les trois Pods sont sur le seul nœud qui satisfait l'obligation.
# ----------------------------------------------------------------------
def test_storage_app_tourne_sur_le_noeud_ssd(host):
    prets: list[dict] = []
    for _ in range(18):
        prets = [
            p for p in _json(host, f"-n {NAMESPACE} get pods -l app={DEPLOYMENT}")["items"]
            if not p["metadata"].get("deletionTimestamp") and p["status"].get("phase") == "Running"
            and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])
        ]
        if len(prets) == 3:
            break
        time.sleep(5)
    assert len(prets) == 3, message(
        en=f"{len(prets)} Pod(s) of {DEPLOYMENT} ready out of 3 after 90 s. A Pod Pending for "
        "affinity says so in kubectl describe pod: no node carries the required label.",
        fr=f"{len(prets)} Pod(s) de {DEPLOYMENT} prêt(s) sur 3 après 90 s. Un Pod Pending pour "
        "affinité le dit dans kubectl describe pod : aucun nœud ne porte le label exigé.",
    )
    ailleurs = [p["metadata"]["name"] for p in prets if p["spec"].get("nodeName") != WORKER]
    assert not ailleurs, message(
        en=f"These Pods of {DEPLOYMENT} run outside {WORKER}: {ailleurs}. Only {WORKER} carries "
        "disktype=ssd: a required affinity on that label leaves no other node. If it were "
        "preferred rather than required, the scheduler would stay free.",
        fr=f"Ces Pods de {DEPLOYMENT} tournent hors de {WORKER} : {ailleurs}. Seul {WORKER} porte "
        "disktype=ssd : une affinité obligatoire sur ce label ne laisse aucun autre nœud. Si elle "
        "était préférée et non obligatoire, le scheduler resterait libre.",
    )


# ----------------------------------------------------------------------
# 4. gpu-app a attendu son label, puis a démarré, sans être recréé.
# ----------------------------------------------------------------------
def test_gpu_app_a_demarre_quand_le_label_est_arrive(host):
    pod: dict = {}
    for _ in range(18):
        res = _kubectl(host, f"-n {NAMESPACE} get pod gpu-app -o json")
        assert res.rc == 0, message(
            en=f"No gpu-app Pod in {NAMESPACE}.",
            fr=f"Aucun Pod gpu-app dans {NAMESPACE}.",
        )
        pod = json.loads(res.stdout)
        if pod["status"].get("phase") == "Running":
            break
        time.sleep(5)
    affinite = ((pod["spec"].get("affinity") or {}).get("nodeAffinity") or {})
    obligatoire = _expressions((affinite.get("requiredDuringSchedulingIgnoredDuringExecution") or {}).get("nodeSelectorTerms") or [])
    assert any(k == "accelerator" and "gpu" in v for k, _, v in obligatoire), message(
        en=f"gpu-app declares no required affinity on accelerator=gpu (seen: {obligatoire}). "
        "Without it, it would have started anywhere, without waiting.",
        fr=f"gpu-app ne déclare pas d'affinité obligatoire sur accelerator=gpu (vu : {obligatoire}). "
        "Sans elle, il aurait démarré n'importe où, sans attendre.",
    )
    assert pod["status"].get("phase") == "Running", message(
        en=f"gpu-app is in phase {pod['status'].get('phase')!r}. It is waiting for a node labelled "
        "accelerator=gpu: once the label is set, the scheduler places it by itself.",
        fr=f"gpu-app est en phase {pod['status'].get('phase')!r}. Il attend un nœud étiqueté "
        "accelerator=gpu : le label posé, le scheduler le place de lui-même.",
    )
    noeud = pod["spec"].get("nodeName")
    labels = _json(host, f"get node {noeud}")["metadata"].get("labels") or {}
    assert labels.get("accelerator") == "gpu", message(
        en=f"gpu-app runs on {noeud}, which does not carry the accelerator=gpu label: it was put "
        "there without going through the scheduler.",
        fr=f"gpu-app tourne sur {noeud}, qui n'a pas le label accelerator=gpu : il y a été mis sans "
        "passer par le scheduler.",
    )
    planifie = [c for c in pod["status"].get("conditions") or [] if c.get("type") == "PodScheduled"]
    assert planifie and planifie[0].get("lastTransitionTime", "") > pod["metadata"]["creationTimestamp"], message(
        en="gpu-app was scheduled at the very moment it was created: it never waited for the label. "
        "The Pod had to be declared before the label existed, and start when it arrives.",
        fr="gpu-app a été planifié à l'instant même de sa création : il n'a jamais attendu le label. "
        "Le Pod devait être déclaré avant que le label existe, et démarrer quand il arrive.",
    )
