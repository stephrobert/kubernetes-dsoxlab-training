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

from conftest import lab_host, lab_target_host, message

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
    return _json(host, f"-n {NAMESPACE} get pods -l app=myapp,version={version}", message(
            en="Cannot read the Pods.",
            fr="Lecture des Pods impossible.",
        ))["items"]


# ----------------------------------------------------------------------
# 1. Les deux versions tournent côte à côte, deux replicas chacune.
# ----------------------------------------------------------------------
def test_les_deux_versions_tournent(host):
    for couleur in ("blue", "green"):
        d = {}
        for _ in range(12):
            d = _json(host, f"-n {NAMESPACE} get deployment app-{couleur}",
                      message(
            en=f"No Deployment app-{couleur} in {NAMESPACE}.",
            fr=f"Aucun Deployment app-{couleur} dans {NAMESPACE}.",
        ))
            if d["status"].get("availableReplicas", 0) == 2:
                break
            time.sleep(5)
        assert d["spec"].get("replicas") == 2, message(
            en=f"app-{couleur} asks for {d['spec'].get('replicas')} replica(s), expected 2.",
            fr=f"app-{couleur} demande {d['spec'].get('replicas')} replica(s), attendu 2.",
        )
        assert d["status"].get("availableReplicas", 0) == 2, message(
            en=f"app-{couleur}: {d['status'].get('availableReplicas', 0)} replica(s) available out of 2.",
            fr=f"app-{couleur} : {d['status'].get('availableReplicas', 0)} replica(s) disponible(s) sur 2.",
        )
        pods = _pods_par_version(host, couleur)
        assert len(pods) >= 2, message(
            en=f"No Pod carries the labels app=myapp and version={couleur}: those are "
            "the labels, on the Pods, that the Service will select.",
            fr=f"Aucun Pod ne porte les labels app=myapp et version={couleur} : ce sont "
            "ces labels, sur les Pods, que le Service sélectionnera.",
        )


# ----------------------------------------------------------------------
# 2. Le Service vise green, et ses endpoints sont exactement les Pods green.
# ----------------------------------------------------------------------
def test_le_service_vise_green_et_seulement_green(host):
    service = _json(host, f"-n {NAMESPACE} get service {SERVICE}", message(
            en=f"No Service {SERVICE} in {NAMESPACE}.",
            fr=f"Aucun Service {SERVICE} dans {NAMESPACE}.",
        ))
    selecteur = service["spec"].get("selector") or {}
    assert selecteur.get("version") == "green", message(
        en=f"The selector of {SERVICE} is {selecteur}: the switch to green has not "
        "been made. It comes down to one selector change, kubectl patch or kubectl edit.",
        fr=f"Le selector de {SERVICE} vaut {selecteur} : la bascule vers green n'est pas "
        "faite. Elle tient en un changement de selector, kubectl patch ou kubectl edit.",
    )
    assert selecteur.get("app") == "myapp", message(
        en=f"The selector of {SERVICE} does not carry app=myapp: it could target Pods "
        "of another application.",
        fr=f"Le selector de {SERVICE} ne porte pas app=myapp : il pourrait viser des Pods "
        "d'une autre application.",
    )
    ports = [p.get("port") for p in service["spec"].get("ports") or []]
    assert PORT in ports, message(
        en=f"{SERVICE} does not listen on {PORT}: ports {ports}.",
        fr=f"{SERVICE} n'écoute pas sur {PORT} : ports {ports}.",
    )
    green = {p["status"].get("podIP") for p in _pods_par_version(host, "green")}
    blue = {p["status"].get("podIP") for p in _pods_par_version(host, "blue")}
    adresses = set()
    for _ in range(12):
        tranches = _json(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}",
                         message(
            en="Cannot read the EndpointSlices.",
            fr="Lecture des EndpointSlices impossible.",
        ))
        adresses = {
            a for t in tranches["items"] for e in t.get("endpoints") or []
            for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")
        }
        if adresses and adresses <= green:
            break
        time.sleep(5)
    assert adresses, message(
        en=f"{SERVICE} has no ready endpoint.",
        fr=f"{SERVICE} n'a aucun endpoint prêt.",
    )
    assert not (adresses & blue), message(
        en=f"Some endpoints of {SERVICE} are still blue Pods: {sorted(adresses & blue)}. "
        "A selector naming only app=myapp catches both versions.",
        fr=f"Des endpoints de {SERVICE} sont encore des Pods blue : {sorted(adresses & blue)}. "
        "Un selector qui ne nomme que app=myapp attrape les deux versions.",
    )
    assert adresses <= green, message(
        en=f"Unexpected endpoints: {sorted(adresses - green)}.",
        fr=f"Endpoints inattendus : {sorted(adresses - green)}.",
    )


# ----------------------------------------------------------------------
# 3. La preuve : toutes les requêtes répondent green.
# ----------------------------------------------------------------------
def test_toutes_les_requetes_repondent_green(host):
    reponses = []
    for _ in range(6):
        res = _kubectl(host, f"-n {NAMESPACE} exec {CLIENT} -- wget -qO- -T 5 http://{SERVICE}:{PORT}/")
        assert res.rc == 0, message(
            en=f"http://{SERVICE}:{PORT}/ does not answer from {CLIENT}: {res.stderr.strip()[:150]}",
            fr=f"http://{SERVICE}:{PORT}/ ne répond pas depuis {CLIENT} : {res.stderr.strip()[:150]}",
        )
        reponses.append(res.stdout.strip())
    assert all(r == "green" for r in reponses), message(
        en=f"Out of six requests, the answers are {reponses}: as long as a single one "
        "answers blue, the switch is not complete, or the green Pods do not answer "
        "with their name.",
        fr=f"Sur six requêtes, les réponses sont {reponses} : tant qu'une seule répond "
        "blue, la bascule n'est pas complète, ou les Pods green ne répondent pas "
        "leur nom.",
    )
