"""test_functional.py : ckad-blue-green-deployment

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. La première lit les deux Deployments ; la deuxième le
selector et les endpoints du Service ; la troisième fait plusieurs requêtes
depuis le client, et c'est elle qui prouve la bascule : un selector correct
avec des Pods qui répondent tous « blue » ne tromperait pas ce test.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
SERVICE = "app-prod"
CLIENT = "client"
PORT = 8080
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


def _pods_par_version(host, version: str) -> list[dict]:
    return _json(host, f"-n {NAMESPACE} get pods -l app=myapp,version={version}", "Lecture des Pods impossible.")["items"]


# ----------------------------------------------------------------------
# 1. Les deux versions tournent côte à côte, deux replicas chacune.
# ----------------------------------------------------------------------
def test_les_deux_versions_tournent(host):
    for couleur in ("blue", "green"):
        d = {}
        for _ in range(12):
            d = _json(host, f"-n {NAMESPACE} get deployment app-{couleur}",
                      f"Aucun Deployment app-{couleur} dans {NAMESPACE}.")
            if d["status"].get("availableReplicas", 0) == 2:
                break
            time.sleep(5)
        assert d["spec"].get("replicas") == 2, f"app-{couleur} demande {d['spec'].get('replicas')} replica(s), attendu 2."
        assert d["status"].get("availableReplicas", 0) == 2, (
            f"app-{couleur} : {d['status'].get('availableReplicas', 0)} replica(s) disponible(s) sur 2."
        )
        pods = _pods_par_version(host, couleur)
        assert len(pods) >= 2, (
            f"Aucun Pod ne porte les labels app=myapp et version={couleur} : ce sont "
            "ces labels, sur les Pods, que le Service sélectionnera."
        )


# ----------------------------------------------------------------------
# 2. Le Service vise green, et ses endpoints sont exactement les Pods green.
# ----------------------------------------------------------------------
def test_le_service_vise_green_et_seulement_green(host):
    service = _json(host, f"-n {NAMESPACE} get service {SERVICE}", f"Aucun Service {SERVICE} dans {NAMESPACE}.")
    selecteur = service["spec"].get("selector") or {}
    assert selecteur.get("version") == "green", (
        f"Le selector de {SERVICE} vaut {selecteur} : la bascule vers green n'est pas "
        "faite. Elle tient en un changement de selector, kubectl patch ou kubectl edit."
    )
    assert selecteur.get("app") == "myapp", (
        f"Le selector de {SERVICE} ne porte pas app=myapp : il pourrait viser des Pods "
        "d'une autre application."
    )
    ports = [p.get("port") for p in service["spec"].get("ports") or []]
    assert PORT in ports, f"{SERVICE} n'écoute pas sur {PORT} : ports {ports}."
    green = {p["status"].get("podIP") for p in _pods_par_version(host, "green")}
    blue = {p["status"].get("podIP") for p in _pods_par_version(host, "blue")}
    adresses = set()
    for _ in range(12):
        tranches = _json(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}",
                         "Lecture des EndpointSlices impossible.")
        adresses = {
            a for t in tranches["items"] for e in t.get("endpoints") or []
            for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")
        }
        if adresses and adresses <= green:
            break
        time.sleep(5)
    assert adresses, f"{SERVICE} n'a aucun endpoint prêt."
    assert not (adresses & blue), (
        f"Des endpoints de {SERVICE} sont encore des Pods blue : {sorted(adresses & blue)}. "
        "Un selector qui ne nomme que app=myapp attrape les deux versions."
    )
    assert adresses <= green, f"Endpoints inattendus : {sorted(adresses - green)}."


# ----------------------------------------------------------------------
# 3. La preuve : toutes les requêtes répondent green.
# ----------------------------------------------------------------------
def test_toutes_les_requetes_repondent_green(host):
    reponses = []
    for _ in range(6):
        res = _kubectl(host, f"-n {NAMESPACE} exec {CLIENT} -- wget -qO- -T 5 http://{SERVICE}:{PORT}/")
        assert res.rc == 0, (
            f"http://{SERVICE}:{PORT}/ ne répond pas depuis {CLIENT} : {res.stderr.strip()[:150]}"
        )
        reponses.append(res.stdout.strip())
    assert all(r == "green" for r in reponses), (
        f"Sur six requêtes, les réponses sont {reponses} : tant qu'une seule répond "
        "blue, la bascule n'est pas complète, ou les Pods green ne répondent pas "
        "leur nom."
    )
