"""test_functional.py : k8s-premier-deploiement

Ces tests lisent l'état du cluster et le fichier ~/demo-app/reponse.html. Un
test vérifie un seul état demandé par l'énoncé.

La mise à l'échelle est jugée sur la génération du Deployment : un Deployment
créé d'emblée à trois réplicas garde la génération 1, une mise à l'échelle la
fait monter. La réponse consignée est comparée à la page que sert vraiment
nginx, lue dans un de ses Pods.

Aucun test n'attend tant que le travail n'est pas commencé : l'attente des
réplicas ne s'ouvre que si le Deployment en demande déjà trois.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "demo-app"
IMAGE = "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
DIGEST = IMAGE.split("@", 1)[1]
REPLICAS = 3
ATTENTE = 60
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _nginx(host) -> dict:
    dep = _json(host, "get deployment nginx")
    assert dep is not None, message(
        en=f"No Deployment nginx in the {NS} namespace. Create the namespace first, then the "
        "Deployment in it, with -n on every command.",
        fr=f"Aucun Deployment nginx dans le namespace {NS}. Créez d'abord le namespace, puis le "
        "Deployment dedans, avec -n à chaque commande.",
    )
    return dep


def _normal(texte: str) -> str:
    return " ".join(texte.split())


# ----------------------------------------------------------------------
# 1. Le Deployment sur l'image épinglée.
# ----------------------------------------------------------------------
def test_le_deployment_nginx_tourne_sur_l_image_epinglee(host):
    image = _nginx(host)["spec"]["template"]["spec"]["containers"][0].get("image", "")
    assert image.split("@", 1)[0] in ("nginx:1.30", "docker.io/library/nginx:1.30") and image.endswith(DIGEST), message(
        en=f"nginx runs {image!r}, expected {IMAGE}. A tag moves, a digest designates one "
        "content and one only: avoid latest, pin the image.",
        fr=f"nginx tourne avec {image!r}, attendu {IMAGE}. Un tag bouge, un digest désigne un "
        "contenu et un seul : évitez latest, épinglez l'image.",
    )


# ----------------------------------------------------------------------
# 2. Mis à l'échelle à trois réplicas disponibles.
# ----------------------------------------------------------------------
def test_nginx_a_ete_mis_a_l_echelle_a_trois_replicas_disponibles(host):
    dep = _nginx(host)
    demandes = dep["spec"].get("replicas", 1)
    assert demandes == REPLICAS, message(
        en=f"nginx asks for {demandes} replica(s), expected {REPLICAS}.",
        fr=f"nginx demande {demandes} réplica(s), attendu {REPLICAS}.",
    )
    assert dep["metadata"].get("generation", 1) >= 2, message(
        en="nginx was created directly with three replicas: the request is to create it with "
        "one, then to scale it. Reread the section of the lesson on scaling.",
        fr="nginx a été créé directement à trois réplicas : la demande est de le créer avec un "
        "seul, puis de le mettre à l'échelle. Relisez la section de la leçon sur la mise à "
        "l'échelle.",
    )
    fin = time.monotonic() + ATTENTE
    disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    while disponibles != REPLICAS and time.monotonic() < fin:
        time.sleep(PAS)
        dep = _nginx(host)
        disponibles = (dep.get("status") or {}).get("availableReplicas") or 0
    assert disponibles == REPLICAS, message(
        en=f"nginx has {disponibles} available replica(s) out of {REPLICAS} after {ATTENTE}s: "
        "kubectl describe deployment nginx -n demo-app says why, in its events.",
        fr=f"nginx a {disponibles} réplica(s) disponible(s) sur {REPLICAS} après {ATTENTE}s : "
        "kubectl describe deployment nginx -n demo-app dit pourquoi, dans ses événements.",
    )


# ----------------------------------------------------------------------
# 3. Le Service et ses trois endpoints prêts.
# ----------------------------------------------------------------------
def test_le_service_nginx_compte_trois_endpoints_prets(host):
    svc = _json(host, "get service nginx")
    assert svc is not None, message(
        en=f"No Service nginx in {NS}: expose the Deployment.",
        fr=f"Aucun Service nginx dans {NS} : exposez le Deployment.",
    )
    tranches = (_json(host, "get endpointslice -l kubernetes.io/service-name=nginx") or {}).get("items") or []
    prets = {
        adresse
        for tranche in tranches
        for point in tranche.get("endpoints") or []
        if (point.get("conditions") or {}).get("ready")
        for adresse in point.get("addresses") or []
    }
    assert len(prets) == REPLICAS, message(
        en=f"The Service nginx counts {len(prets)} ready endpoint(s), expected {REPLICAS}. An "
        "empty list raises no error: compare the Selector of the Service with the labels of "
        "the Pods.",
        fr=f"Le Service nginx compte {len(prets)} endpoint(s) prêt(s), attendu {REPLICAS}. Une "
        "liste vide ne lève aucune erreur : comparez le Selector du Service aux labels des Pods.",
    )


# ----------------------------------------------------------------------
# 4. La réponse HTTP consignée.
# ----------------------------------------------------------------------
def test_la_reponse_consignee_est_la_page_que_sert_nginx(host):
    fichier = host.file(f"{_maison(host)}/{NS}/reponse.html")
    assert fichier.exists and fichier.content_string.strip(), message(
        en="~/demo-app/reponse.html is missing or empty: write in it the answer of "
        "http://nginx read from a client Pod.",
        fr="~/demo-app/reponse.html est absent ou vide : écrivez-y la réponse de http://nginx "
        "lue depuis un Pod client.",
    )
    consignee = _normal(fichier.content_string)
    servie = host.run(f"{ADMIN} -n {NS} exec deploy/nginx -- cat /usr/share/nginx/html/index.html")
    assert servie.rc == 0, message(
        en="The page served by nginx cannot be read: is the Deployment running?",
        fr="La page servie par nginx ne peut pas être lue : le Deployment tourne-t-il ?",
    )
    assert _normal(servie.stdout) in consignee, message(
        en="~/demo-app/reponse.html is not the page nginx serves. Query the Service by its "
        "name from a Pod of the cluster and redirect the whole answer into the file.",
        fr="~/demo-app/reponse.html n'est pas la page que sert nginx. Interrogez le Service par "
        "son nom depuis un Pod du cluster et redirigez la réponse entière dans le fichier.",
    )
