"""test_functional.py : cka-taints-tolerations-placement

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le taint et le label du nœud. La
deuxième et la troisième lisent où chaque Pod tourne réellement. La
quatrième lit ce que prod-app déclare : une tolérance pour le taint et un
nodeSelector sur le label ; un Pod épinglé par nodeName arriverait au même
endroit en sautant le scheduler, et le taint avec lui, ce que ce test refuse.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
WORKER = "k8s-w1.lab"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod_pret(host, nom: str) -> dict:
    pod: dict = {}
    for _ in range(18):
        res = _kubectl(host, f"-n {NAMESPACE} get pod {nom} -o json")
        assert res.rc == 0, f"Aucun Pod {nom} dans {NAMESPACE}."
        pod = json.loads(res.stdout)
        if pod["status"].get("phase") == "Running" and all(
            s.get("ready") for s in pod["status"].get("containerStatuses") or []
        ):
            return pod
        time.sleep(5)
    pytest.fail(
        f"Le Pod {nom} n'est pas prêt après 90 s : phase {pod['status'].get('phase')!r}. "
        "S'il est Pending, kubectl describe pod dit quel nœud le refuse, et pourquoi."
    )


# ----------------------------------------------------------------------
# 1. Le nœud est réservé, et reconnaissable.
# ----------------------------------------------------------------------
def test_le_noeud_porte_le_taint_et_le_label(host):
    res = _kubectl(host, f"get node {WORKER} -o json")
    assert res.rc == 0, f"Le nœud {WORKER} est introuvable."
    noeud = json.loads(res.stdout)
    taints = [(t.get("key"), t.get("value"), t.get("effect")) for t in noeud["spec"].get("taints") or []]
    assert ("env", "prod", "NoSchedule") in taints, (
        f"{WORKER} porte les taints {taints}, pas env=prod:NoSchedule. Un taint se pose avec "
        "kubectl taint nodes <nœud> <clé>=<valeur>:<effet>."
    )
    labels = noeud["metadata"].get("labels") or {}
    assert labels.get("disktype") == "ssd", (
        f"{WORKER} a le label disktype={labels.get('disktype')!r}, attendu ssd. Un taint repousse, "
        "il ne désigne pas : c'est le label qui permettra à prod-app de viser ce nœud."
    )


# ----------------------------------------------------------------------
# 2. prod-app tourne sur le worker réservé.
# ----------------------------------------------------------------------
def test_prod_app_tourne_sur_le_worker(host):
    pod = _pod_pret(host, "prod-app")
    assert pod["spec"].get("nodeName") == WORKER, (
        f"prod-app tourne sur {pod['spec'].get('nodeName')!r} au lieu de {WORKER}. Tolérer le taint "
        "permet d'y aller, seul le nodeSelector sur disktype=ssd l'y oblige."
    )


# ----------------------------------------------------------------------
# 3. dev-app tourne, mais pas sur le worker réservé.
# ----------------------------------------------------------------------
def test_dev_app_tourne_ailleurs(host):
    pod = _pod_pret(host, "dev-app")
    assert pod["spec"].get("nodeName") != WORKER, (
        f"dev-app tourne sur {WORKER}, le nœud réservé. Soit le taint n'était pas posé quand le "
        "Pod a été créé, soit dev-app le tolère : un taint NoSchedule n'expulse pas ce qui est déjà là."
    )


# ----------------------------------------------------------------------
# 4. La preuve : prod-app y est par tolérance et sélection, pas par nodeName.
# ----------------------------------------------------------------------
def test_prod_app_y_est_par_tolerance_et_selection(host):
    pod = _pod_pret(host, "prod-app")
    tolerances = pod["spec"].get("tolerations") or []
    bonnes = [
        t for t in tolerances
        if t.get("key") == "env" and t.get("effect") in ("NoSchedule", None, "")
        and (t.get("operator") == "Exists" or t.get("value") == "prod")
    ]
    assert bonnes, (
        f"prod-app ne déclare aucune tolérance pour env=prod:NoSchedule (tolérances : "
        f"{[(t.get('key'), t.get('value'), t.get('effect')) for t in tolerances]}). Il est sur "
        f"{WORKER} sans tolérer son taint : il y a été épinglé par nodeName, en sautant le "
        "scheduler. Le taint ne protège plus rien de cette façon."
    )
    selecteur = pod["spec"].get("nodeSelector") or {}
    assert selecteur.get("disktype") == "ssd", (
        f"prod-app n'a pas de nodeSelector disktype=ssd (sélecteur : {selecteur}). Sans lui, la "
        "tolérance permet ce nœud sans l'imposer : au prochain redémarrage, il peut partir ailleurs."
    )
