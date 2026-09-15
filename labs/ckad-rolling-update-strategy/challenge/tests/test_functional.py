"""test_functional.py : ckad-rolling-update-strategy

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. La première lit la stratégie ; la deuxième l'image et
les replicas prêts ; la troisième lit les ReplicaSets, et c'est elle qui
prouve qu'une mise à jour progressive a eu lieu et s'est terminée : un
Deployment recréé de zéro en 1.27 n'aurait qu'un ReplicaSet.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
DEPLOYMENT = "webapp"
IMAGE = "nginx:1.27-alpine"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. La stratégie respecte les contraintes.
# ----------------------------------------------------------------------
def test_la_strategie_respecte_les_contraintes(host):
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.")
    strategie = d["spec"].get("strategy") or {}
    assert strategie.get("type") == "RollingUpdate", f"La stratégie est {strategie.get('type')!r}, attendu RollingUpdate."
    ru = strategie.get("rollingUpdate") or {}
    assert str(ru.get("maxSurge")) == "2", (
        f"maxSurge vaut {ru.get('maxSurge')!r}, attendu 2 : au plus deux Pods en trop pendant la bascule. "
        "La valeur par défaut, 25 %, en autoriserait deux sur cinq aussi, mais ce n'est pas ce qui est demandé."
    )
    assert str(ru.get("maxUnavailable")) == "1", (
        f"maxUnavailable vaut {ru.get('maxUnavailable')!r}, attendu 1 : au plus un Pod indisponible à la fois."
    )


# ----------------------------------------------------------------------
# 2. L'image est la nouvelle, et les cinq replicas sont prêts.
# ----------------------------------------------------------------------
def test_la_nouvelle_image_est_prete_au_complet(host):
    d = {}
    for _ in range(18):
        d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.")
        if d["status"].get("readyReplicas", 0) == 5 and d["status"].get("updatedReplicas", 0) == 5:
            break
        time.sleep(5)
    image = d["spec"]["template"]["spec"]["containers"][0].get("image")
    assert image == IMAGE, f"L'image du Deployment est {image!r}, attendu {IMAGE!r}."
    assert d["spec"].get("replicas") == 5, f"replicas vaut {d['spec'].get('replicas')}, attendu 5 : il ne fallait pas y toucher."
    assert d["status"].get("readyReplicas", 0) == 5 and d["status"].get("updatedReplicas", 0) == 5, (
        f"{d['status'].get('readyReplicas', 0)} prêts, {d['status'].get('updatedReplicas', 0)} à jour sur 5 "
        "après 90 s : la mise à jour n'est pas allée au bout. kubectl rollout status le dit."
    )


# ----------------------------------------------------------------------
# 3. Deux révisions : l'ancienne à zéro, la nouvelle au complet.
# ----------------------------------------------------------------------
def test_l_ancienne_revision_est_a_zero_et_la_nouvelle_au_complet(host):
    rs = _json(host, f"-n {NAMESPACE} get replicasets -l app={DEPLOYMENT}", "Lecture des ReplicaSets impossible.")["items"]
    assert len(rs) >= 2, (
        f"{len(rs)} ReplicaSet pour {DEPLOYMENT} : une mise à jour progressive en crée "
        "un nouveau et garde l'ancien à zéro. Un seul ReplicaSet signifie que le "
        "Deployment a été recréé plutôt que mis à jour."
    )
    par_image = {}
    for r in rs:
        image = r["spec"]["template"]["spec"]["containers"][0].get("image")
        par_image[image] = r["status"].get("replicas", 0)
    assert par_image.get(IMAGE) == 5, f"Le ReplicaSet de {IMAGE} porte {par_image.get(IMAGE)} replica(s), attendu 5."
    anciens = {img: n for img, n in par_image.items() if img != IMAGE}
    assert anciens and all(n == 0 for n in anciens.values()), (
        f"Les anciens ReplicaSets portent encore des replicas : {anciens}. La mise à "
        "jour n'est pas terminée, ou elle est bloquée."
    )
