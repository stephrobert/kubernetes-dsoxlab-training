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

from conftest import lab_host, lab_target_host, message

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
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", message(
            en=f"No Deployment {DEPLOYMENT} in {NAMESPACE}.",
            fr=f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.",
        ))
    strategie = d["spec"].get("strategy") or {}
    assert strategie.get("type") == "RollingUpdate", message(
        en=f"The strategy is {strategie.get('type')!r}, expected RollingUpdate.",
        fr=f"La stratégie est {strategie.get('type')!r}, attendu RollingUpdate.",
    )
    ru = strategie.get("rollingUpdate") or {}
    assert str(ru.get("maxSurge")) == "2", message(
        en=f"maxSurge is {ru.get('maxSurge')!r}, expected 2: at most two extra Pods during the switch. "
        "The default, 25 %, would also allow two out of five, but that is not what was asked.",
        fr=f"maxSurge vaut {ru.get('maxSurge')!r}, attendu 2 : au plus deux Pods en trop pendant la bascule. "
        "La valeur par défaut, 25 %, en autoriserait deux sur cinq aussi, mais ce n'est pas ce qui est demandé.",
    )
    assert str(ru.get("maxUnavailable")) == "1", message(
        en=f"maxUnavailable is {ru.get('maxUnavailable')!r}, expected 1: at most one Pod unavailable at a time.",
        fr=f"maxUnavailable vaut {ru.get('maxUnavailable')!r}, attendu 1 : au plus un Pod indisponible à la fois.",
    )


# ----------------------------------------------------------------------
# 2. L'image est la nouvelle, et les cinq replicas sont prêts.
# ----------------------------------------------------------------------
def test_la_nouvelle_image_est_prete_au_complet(host):
    d = {}
    for _ in range(18):
        d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", message(
            en=f"No Deployment {DEPLOYMENT} in {NAMESPACE}.",
            fr=f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.",
        ))
        if d["status"].get("readyReplicas", 0) == 5 and d["status"].get("updatedReplicas", 0) == 5:
            break
        time.sleep(5)
    image = d["spec"]["template"]["spec"]["containers"][0].get("image")
    assert image == IMAGE, message(
        en=f"The Deployment's image is {image!r}, expected {IMAGE!r}.",
        fr=f"L'image du Deployment est {image!r}, attendu {IMAGE!r}.",
    )
    assert d["spec"].get("replicas") == 5, message(
        en=f"replicas is {d['spec'].get('replicas')}, expected 5: it was not to be touched.",
        fr=f"replicas vaut {d['spec'].get('replicas')}, attendu 5 : il ne fallait pas y toucher.",
    )
    assert d["status"].get("readyReplicas", 0) == 5 and d["status"].get("updatedReplicas", 0) == 5, message(
        en=f"{d['status'].get('readyReplicas', 0)} ready, {d['status'].get('updatedReplicas', 0)} up to date out of 5 "
        "after 90 s: the update did not go through. kubectl rollout status says so.",
        fr=f"{d['status'].get('readyReplicas', 0)} prêts, {d['status'].get('updatedReplicas', 0)} à jour sur 5 "
        "après 90 s : la mise à jour n'est pas allée au bout. kubectl rollout status le dit.",
    )


# ----------------------------------------------------------------------
# 3. Deux révisions : l'ancienne à zéro, la nouvelle au complet.
# ----------------------------------------------------------------------
def test_l_ancienne_revision_est_a_zero_et_la_nouvelle_au_complet(host):
    rs = _json(host, f"-n {NAMESPACE} get replicasets -l app={DEPLOYMENT}", message(
            en="Cannot read the ReplicaSets.",
            fr="Lecture des ReplicaSets impossible.",
        ))["items"]
    assert len(rs) >= 2, message(
        en=f"{len(rs)} ReplicaSet for {DEPLOYMENT}: a rolling update creates "
        "a new one and keeps the old one at zero. A single ReplicaSet means the "
        "Deployment was recreated rather than updated.",
        fr=f"{len(rs)} ReplicaSet pour {DEPLOYMENT} : une mise à jour progressive en crée "
        "un nouveau et garde l'ancien à zéro. Un seul ReplicaSet signifie que le "
        "Deployment a été recréé plutôt que mis à jour.",
    )
    par_image = {}
    for r in rs:
        image = r["spec"]["template"]["spec"]["containers"][0].get("image")
        par_image[image] = r["status"].get("replicas", 0)
    assert par_image.get(IMAGE) == 5, message(
        en=f"The ReplicaSet for {IMAGE} carries {par_image.get(IMAGE)} replica(s), expected 5.",
        fr=f"Le ReplicaSet de {IMAGE} porte {par_image.get(IMAGE)} replica(s), attendu 5.",
    )
    anciens = {img: n for img, n in par_image.items() if img != IMAGE}
    assert anciens and all(n == 0 for n in anciens.values()), message(
        en=f"The old ReplicaSets still carry replicas: {anciens}. The update "
        "is not finished, or it is stuck.",
        fr=f"Les anciens ReplicaSets portent encore des replicas : {anciens}. La mise à "
        "jour n'est pas terminée, ou elle est bloquée.",
    )
