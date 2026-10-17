"""test_functional.py : ckad-init-container

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. La première lit la définition du Pod app ; la deuxième
lit les endpoints du Service ; la troisième lit l'état de l'init container,
terminé avec succès, et du conteneur principal, prêt. Un init container qui
n'attendrait rien laisserait un Pod Running sans dépendance : on exige donc
que le gardien vise config-svc, et que la dépendance soit réellement là.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "app"
INIT = "wait-for-config"
MAIN = "main"
SERVEUR = "config-server"
SERVICE = "config-svc"
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
# 1. Le Pod app a son gardien, et il vise le bon Service.
# ----------------------------------------------------------------------
def test_le_pod_a_un_init_container_qui_attend_le_service(host):
    pod = _json(host, f"-n {NAMESPACE} get pod {POD}", message(
            en=f"No Pod {POD} in {NAMESPACE}.",
            fr=f"Aucun Pod {POD} dans {NAMESPACE}.",
        ))
    inits = {c["name"]: c for c in pod["spec"].get("initContainers") or []}
    assert INIT in inits, message(
        en=f"Pod {POD} has no init container {INIT}. Init containers are "
        f"declared under spec.initContainers, not under containers. Seen: {sorted(inits) or 'none'}",
        fr=f"Le Pod {POD} n'a pas d'init container {INIT}. Les init containers se "
        f"déclarent sous spec.initContainers, pas sous containers. Vus : {sorted(inits) or 'aucun'}",
    )
    commande = " ".join(inits[INIT].get("command") or []) + " " + " ".join(inits[INIT].get("args") or [])
    assert SERVICE in commande, message(
        en=f"Init container {INIT} does not wait for {SERVICE}: its command does not "
        "mention it. A gatekeeper that waits for nothing lets the application start "
        "without its dependency.",
        fr=f"L'init container {INIT} n'attend pas {SERVICE} : sa commande ne le "
        "mentionne pas. Un gardien qui n'attend rien laisse démarrer l'application "
        "sans sa dépendance.",
    )
    principaux = [c["name"] for c in pod["spec"]["containers"]]
    assert MAIN in principaux, message(
        en=f"The main container must be named {MAIN}: seen {principaux}.",
        fr=f"Le conteneur principal doit s'appeler {MAIN} : vus {principaux}.",
    )


# ----------------------------------------------------------------------
# 2. La dépendance est là : config-server, sélectionné par config-svc.
# ----------------------------------------------------------------------
def test_la_dependance_repond_derriere_le_service(host):
    serveur = _json(host, f"-n {NAMESPACE} get pod {SERVEUR}",
                    f"Aucun Pod {SERVEUR} dans {NAMESPACE} : rien ne peut répondre derrière {SERVICE}.")
    assert (serveur["metadata"].get("labels") or {}).get("app") == "config", message(
        en=f"{SERVEUR} does not carry the app=config label: the Service does not select it. "
        f"Labels: {serveur['metadata'].get('labels')}",
        fr=f"{SERVEUR} ne porte pas le label app=config : le Service ne le sélectionne pas. "
        f"Labels : {serveur['metadata'].get('labels')}",
    )
    prets = []
    for _ in range(12):
        tranches = _json(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}",
                         message(
            en="Cannot read the EndpointSlices.",
            fr="Lecture des EndpointSlices impossible.",
        ))
        prets = [
            a for t in tranches["items"] for e in t.get("endpoints") or []
            for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")
        ]
        if prets:
            break
        time.sleep(5)
    assert prets, message(
        en=f"{SERVICE} still has no ready endpoint: {SERVEUR} exists but is not "
        "ready, or the Service does not select it.",
        fr=f"{SERVICE} n'a toujours aucun endpoint prêt : {SERVEUR} existe mais n'est "
        "pas prêt, ou le Service ne le sélectionne pas.",
    )


# ----------------------------------------------------------------------
# 3. L'init s'est terminé avec succès, et app tourne.
# ----------------------------------------------------------------------
def test_l_init_est_termine_et_app_tourne(host):
    pod, etat_init = {}, {}
    for _ in range(18):
        pod = _json(host, f"-n {NAMESPACE} get pod {POD}", message(
            en=f"No Pod {POD} in {NAMESPACE}.",
            fr=f"Aucun Pod {POD} dans {NAMESPACE}.",
        ))
        statuts = {s["name"]: s for s in pod["status"].get("initContainerStatuses") or []}
        etat_init = (statuts.get(INIT) or {}).get("state") or {}
        if pod["status"].get("phase") == "Running" and "terminated" in etat_init:
            break
        time.sleep(5)
    assert "terminated" in etat_init, message(
        en=f"Init container {INIT} has not finished: state {etat_init}. As long as it "
        f"runs, {SERVICE} does not answer it: check what it is waiting for, and what "
        "stands behind the Service. Its logs say where it stands.",
        fr=f"L'init container {INIT} n'est pas terminé : état {etat_init}. Tant qu'il "
        f"tourne, {SERVICE} ne lui répond pas : vérifiez ce qu'il attend, et ce qui "
        "se tient derrière le Service. Ses logs disent où il en est.",
    )
    assert etat_init["terminated"].get("reason") == "Completed", message(
        en=f"The init container ended in {etat_init['terminated'].get('reason')!r} "
        "and not Completed: it exits with an error instead of waiting.",
        fr=f"L'init container s'est terminé en {etat_init['terminated'].get('reason')!r} "
        "et non Completed : il sort en erreur au lieu d'attendre.",
    )
    assert pod["status"].get("phase") == "Running", message(
        en=f"The init container has finished but the Pod is in phase {pod['status'].get('phase')!r}.",
        fr=f"L'init est terminé mais le Pod est en phase {pod['status'].get('phase')!r}.",
    )
