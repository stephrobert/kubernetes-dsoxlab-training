"""test_functional.py : ckad-kustomize-overlays

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées, ni les
fichiers de l'apprenant : ce qui compte, c'est ce que le cluster porte.

Trois affirmations. Les deux premières lisent chaque environnement, avec
les endpoints de son Service, ce qui prouve que le label ajouté est entré
dans les selectors. La troisième compare les deux environnements : une même
base donne une même structure.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

ENVIRONNEMENTS = {"dev": 1, "prod": 3}
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


def _verifier_environnement(host, env: str, replicas: int) -> dict:
    deploiement = f"{env}-app"
    service = f"{env}-app-svc"
    d = {}
    for _ in range(18):
        d = _json(host, f"-n {env} get deployment {deploiement}",
                  f"Aucun Deployment {deploiement} dans {env} : le préfixe {env}- et le namespace "
                  "viennent de l'overlay, kubectl apply -k les applique.")
        if d["status"].get("availableReplicas", 0) == replicas:
            break
        time.sleep(5)
    assert d["spec"].get("replicas") == replicas, (
        f"{deploiement} demande {d['spec'].get('replicas')} replica(s), attendu {replicas} : "
        "c'est l'overlay qui change ce nombre, pas la base."
    )
    assert d["status"].get("availableReplicas", 0) == replicas, (
        f"{deploiement} : {d['status'].get('availableReplicas', 0)} disponible(s) sur {replicas}."
    )
    pods = _json(host, f"-n {env} get pods -l app=app", "Lecture des Pods impossible.")["items"]
    sans_label = [p["metadata"]["name"] for p in pods if (p["metadata"].get("labels") or {}).get("env") != env]
    assert pods and not sans_label, (
        f"Des Pods de {deploiement} ne portent pas env={env} : {sans_label or 'aucun Pod'}. Le label "
        "doit atteindre le template des Pods, pas seulement le Deployment."
    )
    tranches = _json(host, f"-n {env} get endpointslices -l kubernetes.io/service-name={service}",
                     f"Aucun Service {service} dans {env}.")
    prets = [a for t in tranches["items"] for e in t.get("endpoints") or []
             for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")]
    assert len(prets) == replicas, (
        f"{service} a {len(prets)} endpoint(s) prêt(s), attendu {replicas}. Si le label "
        f"env={env} est sur les Pods mais pas dans le selector du Service, ou l'inverse, "
        "le Service ne trouve plus ses Pods."
    )
    return d


# ----------------------------------------------------------------------
# 1 et 2. Chaque environnement tourne, avec son nombre de replicas.
# ----------------------------------------------------------------------
def test_dev_tourne_avec_un_replica(host):
    _verifier_environnement(host, "dev", 1)


def test_prod_tourne_avec_trois_replicas(host):
    _verifier_environnement(host, "prod", 3)


# ----------------------------------------------------------------------
# 3. Une même base : même image, même port, même structure.
# ----------------------------------------------------------------------
def test_les_deux_environnements_viennent_de_la_meme_base(host):
    structures = {}
    for env in ENVIRONNEMENTS:
        d = _json(host, f"-n {env} get deployment {env}-app", f"Aucun Deployment {env}-app.")
        c = d["spec"]["template"]["spec"]["containers"][0]
        structures[env] = (c.get("image"), tuple(p.get("containerPort") for p in c.get("ports") or []), c.get("name"))
    assert structures["dev"] == structures["prod"], (
        f"dev et prod divergent : {structures}. Une même base donne la même image, le "
        "même port et le même nom de conteneur ; seuls namespace, replicas, préfixe et "
        "label changent."
    )
    assert structures["dev"][0] == "nginx:1.27-alpine", f"L'image de la base est {structures['dev'][0]!r}, attendu nginx:1.27-alpine."
