"""test_functional.py : ckad-init-container

Ces tests lisent l'état du cluster, jamais les commandes tapées. Un test
vérifie un seul état demandé par l'énoncé.

Depuis le 2026-11-20, le challenge ne reprend plus le scénario de la leçon
(app, config-svc sur le port 80) : le Service tarifs-svc écoute sur le port
8080, et un Pod facturation tourne déjà avec un gardien qui ne fait qu'un
nslookup. Un http://tarifs-svc/ recopié de la leçon attend sans fin.

Le passage seul en Running se prouve par l'attente du gardien : il tournait
déjà quand tarifs est devenu Ready (ou il avait déjà échoué au moins une
fois), et il s'est terminé après. Les dates de Kubernetes sont à la seconde,
et les événements Scheduled de ce cluster n'ont pas d'eventTime (mesuré le
2026-11-20) : les égalités sont donc acceptées dans les deux sens. Deux Pods
créés dans la même seconde ne font pas échouer un bon travail ; un tarifs
prêt avant le démarrage du gardien, lui, est refusé.

Tous échouent avant le travail : tarifs n'existe pas, et le gardien de
facturation n'attend aucune réponse.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "facturation"
INIT = "attendre-tarifs"
MAIN = "main"
SERVEUR = "tarifs"
SERVICE = "tarifs-svc"
PORT = "8080"
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


def _attendre_facturation(host) -> dict | None:
    """facturation, attendu Running et init terminé, s'il existe et que tarifs est là."""
    pod = _json(host, f"-n {NS} get pod {POD}")
    if pod is None or _json(host, f"-n {NS} get pod {SERVEUR}") is None:
        return pod
    fin = time.monotonic() + ATTENTE
    while not (pod["status"].get("phase") == "Running" and "terminated" in _etat_init(pod)) \
            and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _json(host, f"-n {NS} get pod {POD}") or pod
    return pod


def _pret_depuis(pod: dict) -> str:
    """Date à laquelle le Pod est devenu Ready, chaîne vide s'il ne l'est pas."""
    for c in (pod.get("status") or {}).get("conditions") or []:
        if c.get("type") == "Ready" and c.get("status") == "True":
            return c.get("lastTransitionTime") or ""
    return ""


def _statut_init(pod: dict) -> dict:
    statuts = {s["name"]: s for s in (pod.get("status") or {}).get("initContainerStatuses") or []}
    return statuts.get(INIT) or {}


# ----------------------------------------------------------------------
# 1. facturation a un gardien qui attend une réponse de tarifs-svc:8080.
# ----------------------------------------------------------------------
def test_facturation_a_un_gardien_qui_attend_tarifs_svc(host):
    pod = _json(host, f"-n {NS} get pod {POD}")
    assert pod is not None, message(
        en=f"No Pod {POD} in {NS}.",
        fr=f"Aucun Pod {POD} dans {NS}.",
    )
    inits = {c["name"]: c for c in pod["spec"].get("initContainers") or []}
    commande = " ".join((inits.get(INIT) or {}).get("command") or []) + " " + \
        " ".join((inits.get(INIT) or {}).get("args") or [])
    assert INIT in inits and SERVICE in commande and PORT in commande, message(
        en=f"{POD} has no init container {INIT} that waits for an answer from {SERVICE} on the port "
        f"the Service listens on (init containers seen: {sorted(inits) or 'none'}, command: "
        f"{commande.strip() or 'none'}). A gatekeeper that only resolves a name waits for nothing: "
        "a Service is in the DNS as soon as it exists.",
        fr=f"{POD} n'a pas d'init container {INIT} qui attend une réponse de {SERVICE} sur le port où "
        f"le Service écoute (init containers vus : {sorted(inits) or 'aucun'}, commande : "
        f"{commande.strip() or 'aucune'}). Un gardien qui ne fait que résoudre un nom n'attend rien : "
        "un Service est dans le DNS dès qu'il existe.",
    )
    principaux = {c["name"]: c.get("image") for c in pod["spec"]["containers"]}
    assert principaux.get(MAIN) == IMAGE, message(
        en=f"The main container must be {MAIN}, on the image of the requirements pinned by digest: "
        f"seen {principaux}.",
        fr=f"Le conteneur principal doit être {MAIN}, sur l'image du cahier des charges épinglée par "
        f"digest : vu {principaux}.",
    )


# ----------------------------------------------------------------------
# 2. tarifs répond derrière le Service, sur le port 8080.
# ----------------------------------------------------------------------
def _prets(host) -> int:
    tranches = _json(host, f"-n {NS} get endpointslices -l kubernetes.io/service-name={SERVICE}") or {}
    return sum(1 for t in tranches.get("items", []) for e in t.get("endpoints") or []
               if (e.get("conditions") or {}).get("ready"))


def test_tarifs_repond_derriere_tarifs_svc(host):
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
    ip = host.run(f"{ADMIN} -n {NS} get service {SERVICE} -o jsonpath='{{.spec.clusterIP}}'").stdout.strip()
    res = host.run(f"curl -sS -m 5 http://{ip}:{PORT}/")
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en=f"{SERVICE} does not serve the nginx page on port {PORT}: {res.stderr.strip()[:120]}",
        fr=f"{SERVICE} ne sert pas la page nginx sur le port {PORT} : {res.stderr.strip()[:120]}",
    )


# ----------------------------------------------------------------------
# 3. L'init container s'est terminé avec succès.
# ----------------------------------------------------------------------
def test_l_init_container_s_est_termine_avec_succes(host):
    assert _json(host, f"-n {NS} get pod {SERVEUR}") is not None, message(
        en=f"No Pod {SERVEUR} in {NS}: the gatekeeper has nothing to wait for yet.",
        fr=f"Aucun Pod {SERVEUR} dans {NS} : le gardien n'a encore rien à attendre.",
    )
    pod = _attendre_facturation(host)
    inits = {c["name"]: c for c in ((pod or {}).get("spec") or {}).get("initContainers") or []}
    commande = " ".join((inits.get(INIT) or {}).get("command") or []) + " " + \
        " ".join((inits.get(INIT) or {}).get("args") or [])
    assert PORT in commande, message(
        en=f"The init container {INIT} that ran does not query {SERVICE} on port {PORT}: its success "
        "proves nothing.",
        fr=f"L'init container {INIT} qui a tourné n'interroge pas {SERVICE} sur le port {PORT} : sa "
        "réussite ne prouve rien.",
    )
    etat = _etat_init(pod or {})
    raison = (etat.get("terminated") or {}).get("reason")
    assert raison == "Completed", message(
        en=f"The init container {INIT} has not completed successfully (state: {etat or 'none'}). As long "
        f"as it runs, {SERVICE} does not answer it on the port it asks; if it ended in error, it gave "
        "up. Its logs say where it stands.",
        fr=f"L'init container {INIT} ne s'est pas terminé avec succès (état : {etat or 'aucun'}). Tant "
        f"qu'il tourne, {SERVICE} ne lui répond pas sur le port qu'il interroge ; s'il a fini en erreur, "
        "il a abandonné. Ses logs disent où il en est.",
    )


# ----------------------------------------------------------------------
# 4. facturation est passé seul en Running quand tarifs a répondu.
# ----------------------------------------------------------------------
def test_facturation_est_passe_seul_en_running_quand_tarifs_a_repondu(host):
    pod = _attendre_facturation(host)
    serveur = _json(host, f"-n {NS} get pod {SERVEUR}")
    assert pod is not None and serveur is not None, message(
        en=f"{POD} and {SERVEUR} must both exist.",
        fr=f"{POD} et {SERVEUR} doivent exister tous les deux.",
    )
    pret = _pret_depuis(serveur)
    statut = _statut_init(pod)
    termine = (statut.get("state") or {}).get("terminated") or {}
    debut, fin = termine.get("startedAt") or "", termine.get("finishedAt") or ""
    tournait = bool(pret) and ((bool(debut) and debut <= pret) or statut.get("restartCount", 0) > 0)
    apres = bool(pret) and bool(fin) and fin >= pret
    assert tournait and apres and pod["status"].get("phase") == "Running", message(
        en=f"{POD} is in phase {pod['status'].get('phase')!r}. Its init container "
        f"{'was already running' if tournait else 'was not running yet'} when {SERVEUR} became ready, "
        f"and ended {'after' if apres else 'before'} that moment. Expected: {POD} created first, "
        "waiting in Init, then Running on its own once the dependency answered.",
        fr=f"{POD} est en phase {pod['status'].get('phase')!r}. Son init container "
        f"{'tournait déjà' if tournait else 'ne tournait pas encore'} quand {SERVEUR} est devenu prêt, "
        f"et s'est terminé {'après' if apres else 'avant'} ce moment. Attendu : {POD} créé d'abord, "
        "en attente dans Init, puis Running seul une fois la dépendance prête.",
    )
