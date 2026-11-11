"""test_functional.py : ckad-init-container

Ces tests lisent l'état du cluster, jamais les commandes tapées. Un test
vérifie un seul état demandé par l'énoncé.

Le passage seul en Running se prouve par les dates : app a été créé AVANT
config-server, et c'est le même Pod qui tourne ensuite. Un app supprimé puis
recréé après la dépendance n'a rien attendu.

Tous échouent avant le travail : ni app ni config-server n'existent. Une
attente ne s'ouvre que si l'objet attendu existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "app"
INIT = "wait-for-config"
MAIN = "main"
SERVEUR = "config-server"
SERVICE = "config-svc"
IMAGE = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 90
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _etat_init(pod: dict) -> dict:
    statuts = {s["name"]: s for s in (pod.get("status") or {}).get("initContainerStatuses") or []}
    return (statuts.get(INIT) or {}).get("state") or {}


def _attendre_app(host) -> dict | None:
    """app, attendu Running et init terminé, s'il existe et que la dépendance est là."""
    pod = _json(host, f"-n {NS} get pod {POD}")
    if pod is None or _json(host, f"-n {NS} get pod {SERVEUR}") is None:
        return pod
    fin = time.monotonic() + ATTENTE
    while not (pod["status"].get("phase") == "Running" and "terminated" in _etat_init(pod)) \
            and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _json(host, f"-n {NS} get pod {POD}") or pod
    return pod


# ----------------------------------------------------------------------
# 1. app a un gardien qui attend config-svc, puis son conteneur principal.
# ----------------------------------------------------------------------
def test_app_a_un_init_container_qui_attend_config_svc(host):
    pod = _json(host, f"-n {NS} get pod {POD}")
    assert pod is not None, message(
        en=f"No Pod {POD} in {NS}.",
        fr=f"Aucun Pod {POD} dans {NS}.",
    )
    inits = {c["name"]: c for c in pod["spec"].get("initContainers") or []}
    commande = " ".join((inits.get(INIT) or {}).get("command") or []) + " " + \
        " ".join((inits.get(INIT) or {}).get("args") or [])
    assert INIT in inits and SERVICE in commande, message(
        en=f"{POD} has no init container {INIT} that waits for {SERVICE} (init containers seen: "
        f"{sorted(inits) or 'none'}). A gatekeeper that waits for nothing lets the application start "
        "without its dependency.",
        fr=f"{POD} n'a pas d'init container {INIT} qui attend {SERVICE} (init containers vus : "
        f"{sorted(inits) or 'aucun'}). Un gardien qui n'attend rien laisse démarrer l'application "
        "sans sa dépendance.",
    )
    principaux = {c["name"]: c.get("image") for c in pod["spec"]["containers"]}
    assert principaux.get(MAIN) == IMAGE, message(
        en=f"The main container must be {MAIN}, on the image of the requirements pinned by digest: "
        f"seen {principaux}.",
        fr=f"Le conteneur principal doit être {MAIN}, sur l'image du cahier des charges épinglée par "
        f"digest : vu {principaux}.",
    )


# ----------------------------------------------------------------------
# 2. La dépendance répond derrière le Service.
# ----------------------------------------------------------------------
def _prets(host) -> int:
    tranches = _json(host, f"-n {NS} get endpointslices -l kubernetes.io/service-name={SERVICE}") or {}
    return sum(1 for t in tranches.get("items", []) for e in t.get("endpoints") or []
               if (e.get("conditions") or {}).get("ready"))


def test_config_server_repond_derriere_config_svc(host):
    serveur = _json(host, f"-n {NS} get pod {SERVEUR}")
    assert serveur is not None, message(
        en=f"No Pod {SERVEUR} in {NS}: nothing can answer behind {SERVICE}.",
        fr=f"Aucun Pod {SERVEUR} dans {NS} : rien ne peut répondre derrière {SERVICE}.",
    )
    fin = time.monotonic() + ATTENTE
    while _prets(host) == 0 and time.monotonic() < fin:
        time.sleep(PAS)
    assert _prets(host) > 0, message(
        en=f"{SERVICE} has no ready endpoint: {SERVEUR} exists, but it is not ready or the Service "
        f"does not select it (labels of {SERVEUR}: {serveur['metadata'].get('labels')}).",
        fr=f"{SERVICE} n'a aucun endpoint prêt : {SERVEUR} existe, mais il n'est pas prêt ou le Service "
        f"ne le sélectionne pas (labels de {SERVEUR} : {serveur['metadata'].get('labels')}).",
    )


# ----------------------------------------------------------------------
# 3. L'init container s'est terminé avec succès.
# ----------------------------------------------------------------------
def test_l_init_container_s_est_termine_avec_succes(host):
    pod = _attendre_app(host)
    etat = _etat_init(pod or {})
    raison = (etat.get("terminated") or {}).get("reason")
    assert raison == "Completed", message(
        en=f"The init container {INIT} has not completed successfully (state: {etat or 'none'}). As long "
        f"as it runs, {SERVICE} does not answer it; if it ended in error, it gave up instead of "
        "waiting. Its logs say where it stands.",
        fr=f"L'init container {INIT} ne s'est pas terminé avec succès (état : {etat or 'aucun'}). Tant "
        f"qu'il tourne, {SERVICE} ne lui répond pas ; s'il a fini en erreur, il a abandonné au lieu "
        "d'attendre. Ses logs disent où il en est.",
    )


# ----------------------------------------------------------------------
# 4. app est passé seul en Running quand la dépendance a répondu.
# ----------------------------------------------------------------------
def test_app_est_passe_seul_en_running_quand_la_dependance_a_repondu(host):
    pod = _attendre_app(host)
    serveur = _json(host, f"-n {NS} get pod {SERVEUR}")
    assert pod is not None and serveur is not None, message(
        en=f"{POD} and {SERVEUR} must both exist.",
        fr=f"{POD} et {SERVEUR} doivent exister tous les deux.",
    )
    avant = pod["metadata"]["creationTimestamp"] < serveur["metadata"]["creationTimestamp"]
    assert avant and pod["status"].get("phase") == "Running", message(
        en=f"{POD} is in phase {pod['status'].get('phase')!r} and was created "
        f"{'before' if avant else 'after'} {SERVEUR}. Expected: {POD} created first, waiting in Init, "
        "then Running on its own once the dependency answered, without being recreated.",
        fr=f"{POD} est en phase {pod['status'].get('phase')!r} et a été créé "
        f"{'avant' if avant else 'après'} {SERVEUR}. Attendu : {POD} créé d'abord, en attente dans "
        "Init, puis Running seul une fois la dépendance prête, sans avoir été recréé.",
    )
