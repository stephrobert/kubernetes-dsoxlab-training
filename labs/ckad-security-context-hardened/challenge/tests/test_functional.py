"""test_functional.py : ckad-security-context-hardened

Ces tests lisent l'état du CLUSTER et du CONTENEUR, jamais les commandes
tapées.

Quatre affirmations. La première lit la définition du Pod ; les trois autres
prouvent que le durcissement AGIT et que l'application vit malgré lui : on
vérifie l'utilisateur réel du processus, on tente une écriture qui doit être
refusée, et on interroge le serveur. Un Pod durci qui ne sert rien ne vaut
pas mieux qu'un Pod qui sert en root.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "hardened"
UID = 1000
PORT = 8080
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _pod(host) -> dict:
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, message(
        en=f"No Pod {POD} in {NAMESPACE}.",
        fr=f"Aucun Pod {POD} dans {NAMESPACE}.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Le Pod tourne, et sa définition porte le durcissement demandé.
# ----------------------------------------------------------------------
def test_le_pod_tourne_durci(host):
    pod = {}
    for _ in range(12):
        pod = _pod(host)
        if pod["status"].get("phase") == "Running":
            break
        time.sleep(5)
    statut = (pod["status"].get("containerStatuses") or [{}])[0]
    raison = ((statut.get("state") or {}).get("waiting") or {}).get("reason")
    assert pod["status"].get("phase") == "Running", message(
        en=f"Pod {POD} is in phase {pod['status'].get('phase')!r}, reason {raison}, "
        f"restarts {statut.get('restartCount')}. A server that cannot "
        "write where it needs to exits at startup: its logs say which "
        "path it wanted to write, and an emptyDir mounted there is enough. "
        "CreateContainerConfigError with runAsNonRoot means the image "
        "would run as root: set runAsUser.",
        fr=f"Le Pod {POD} est en phase {pod['status'].get('phase')!r}, raison {raison}, "
        f"redémarrages {statut.get('restartCount')}. Un serveur qui ne peut pas "
        "écrire là où il en a besoin sort au démarrage : ses logs disent quel "
        "chemin il voulait écrire, et un emptyDir monté là suffit. "
        "CreateContainerConfigError avec runAsNonRoot signifie que l'image "
        "tournerait en root : imposez runAsUser.",
    )
    ctx_pod = pod["spec"].get("securityContext") or {}
    conteneur = pod["spec"]["containers"][0]
    ctx = conteneur.get("securityContext") or {}
    assert ctx.get("runAsNonRoot", ctx_pod.get("runAsNonRoot")) is True, message(
        en="runAsNonRoot is not true: nothing stops the image from running as root.",
        fr="runAsNonRoot n'est pas à true : rien n'interdit à l'image de tourner en root.",
    )
    assert ctx.get("runAsUser", ctx_pod.get("runAsUser")) == UID, message(
        en=f"runAsUser is {ctx.get('runAsUser', ctx_pod.get('runAsUser'))!r}, expected {UID}.",
        fr=f"runAsUser vaut {ctx.get('runAsUser', ctx_pod.get('runAsUser'))!r}, attendu {UID}.",
    )
    assert ctx.get("allowPrivilegeEscalation") is False, message(
        en="allowPrivilegeEscalation is not false on the container: a setuid "
        "binary could still regain privileges.",
        fr="allowPrivilegeEscalation n'est pas à false sur le conteneur : un binaire "
        "setuid pourrait encore remonter les privilèges.",
    )
    assert ctx.get("readOnlyRootFilesystem") is True, message(
        en="readOnlyRootFilesystem is not true on the container.",
        fr="readOnlyRootFilesystem n'est pas à true sur le conteneur.",
    )
    drop = [c.upper() for c in (ctx.get("capabilities") or {}).get("drop") or []]
    assert "ALL" in drop, message(
        en=f"The capabilities are not all dropped: drop is {drop or 'nothing'}. "
        "The expected list is ALL, not an enumeration.",
        fr=f"Les capabilities ne sont pas toutes retirées : drop vaut {drop or 'rien'}. "
        "La liste attendue est ALL, pas une énumération.",
    )


# ----------------------------------------------------------------------
# 2. Le processus est bien l'utilisateur 1000.
# ----------------------------------------------------------------------
def test_le_processus_est_l_utilisateur_1000(host):
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- id -u")
    assert res.rc == 0, message(
        en=f"Cannot exec into {POD}: {res.stderr.strip()[:150]}",
        fr=f"exec impossible dans {POD} : {res.stderr.strip()[:150]}",
    )
    assert res.stdout.strip() == str(UID), message(
        en=f"Inside the container, id -u returns {res.stdout.strip()!r} and not {UID}: the "
        "declared securityContext is not the one that applies.",
        fr=f"Dans le conteneur, id -u rend {res.stdout.strip()!r} et non {UID} : le "
        "securityContext déclaré n'est pas celui qui s'applique.",
    )


# ----------------------------------------------------------------------
# 3. La racine est en lecture seule, et l'application a ses espaces.
# ----------------------------------------------------------------------
def test_la_racine_est_en_lecture_seule(host):
    ecriture = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- sh -c 'touch /etc/preuve 2>&1; echo CODE=$?'")
    assert "CODE=0" not in ecriture.stdout, message(
        en="A write into /etc SUCCEEDED: the container's root is not "
        f"read-only. Output: {ecriture.stdout.strip()[:120]}",
        fr="Une écriture dans /etc a RÉUSSI : la racine du conteneur n'est pas en "
        f"lecture seule. Sortie : {ecriture.stdout.strip()[:120]}",
    )
    tmp = _kubectl(host, f"-n {NAMESPACE} exec {POD} -- sh -c 'touch /tmp/preuve 2>&1; echo CODE=$?'")
    assert "CODE=0" in tmp.stdout, message(
        en="The server has no writable space in /tmp: that is where it puts "
        f"its pid file. An emptyDir mounted on /tmp gives it back. Output: {tmp.stdout.strip()[:120]}",
        fr="Le serveur n'a aucun espace d'écriture dans /tmp : c'est là qu'il pose "
        f"son fichier pid. Un emptyDir monté sur /tmp le lui rend. Sortie : {tmp.stdout.strip()[:120]}",
    )


# ----------------------------------------------------------------------
# 4. L'application sert : le durcissement ne l'a pas tuée.
# ----------------------------------------------------------------------
def test_l_application_repond(host):
    ip = _pod(host)["status"].get("podIP")
    assert ip, message(
        en="The Pod has no IP address: it did not start.",
        fr="Le Pod n'a pas d'adresse IP : il n'a pas démarré.",
    )
    res = host.run(f"curl -sS -m 5 http://{ip}:{PORT}/")
    assert res.rc == 0 and "nginx" in res.stdout.lower(), message(
        en=f"Nothing answers on http://{ip}:{PORT}/ from the node. The Pod may be "
        "Running without nginx having been able to start: look at its logs, it says "
        f"what it cannot write. Output: {(res.stdout + res.stderr).strip()[:150]}",
        fr=f"Rien ne répond sur http://{ip}:{PORT}/ depuis le nœud. Le Pod est peut-être "
        "Running sans que nginx ait pu démarrer : regardez ses logs, il dit ce "
        f"qu'il ne peut pas écrire. Sortie : {(res.stdout + res.stderr).strip()[:150]}",
    )
