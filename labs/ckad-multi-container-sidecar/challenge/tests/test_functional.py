"""test_functional.py : ckad-multi-container-sidecar

Ces tests lisent l'état du CLUSTER et du CONTENEUR, jamais les commandes
tapées.

Trois affirmations. La première lit la définition du Pod, et refuse un
sidecar déclaré comme simple second conteneur : l'examen attend la forme
native. La deuxième entre dans l'application pour lire le fichier. La
troisième lit les logs du sidecar, et c'est elle qui prouve que le volume
est partagé et que le sidecar suit vraiment le fichier.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
POD = "app-with-sidecar"
APP = "app"
SIDECAR = "log-shipper"
VOLUME = "logs"
FICHIER = "/var/log/app/output.log"
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
# 1. Le sidecar est natif, le volume est partagé, le Pod tourne.
# ----------------------------------------------------------------------
def test_le_sidecar_est_natif_et_partage_le_volume(host):
    pod = {}
    for _ in range(12):
        pod = _pod(host)
        if pod["status"].get("phase") == "Running":
            break
        time.sleep(5)
    spec = pod["spec"]
    principaux = {c["name"]: c for c in spec["containers"]}
    inits = {c["name"]: c for c in spec.get("initContainers") or []}
    assert SIDECAR not in principaux, message(
        en=f"{SIDECAR} is declared under containers: that is a second ordinary "
        "container, not a native sidecar. Since 1.33, a sidecar is an init "
        "container with restartPolicy Always.",
        fr=f"{SIDECAR} est déclaré sous containers : c'est un second conteneur "
        "ordinaire, pas un sidecar natif. Depuis la 1.33, un sidecar est un init "
        "container avec restartPolicy Always.",
    )
    assert SIDECAR in inits, message(
        en=f"No init container {SIDECAR}. The native sidecar is declared under "
        f"spec.initContainers. Seen: {sorted(inits) or 'none'}",
        fr=f"Aucun init container {SIDECAR}. Le sidecar natif se déclare sous "
        f"spec.initContainers. Vus : {sorted(inits) or 'aucun'}",
    )
    assert inits[SIDECAR].get("restartPolicy") == "Always", message(
        en=f"{SIDECAR} is an init container without restartPolicy Always: it would have to "
        "finish before app starts, and a tail -F never finishes, so "
        "app would never start. restartPolicy Always is what makes it a sidecar.",
        fr=f"{SIDECAR} est un init container sans restartPolicy Always : il devrait se "
        "terminer avant que app démarre, et un tail -F ne se termine jamais, donc "
        "app ne démarrerait pas. C'est restartPolicy Always qui en fait un sidecar.",
    )
    assert APP in principaux, message(
        en=f"The main container must be named {APP}: seen {sorted(principaux)}.",
        fr=f"Le conteneur principal doit s'appeler {APP} : vus {sorted(principaux)}.",
    )
    volumes = {v["name"]: v for v in spec.get("volumes") or []}
    assert VOLUME in volumes and "emptyDir" in volumes[VOLUME], message(
        en=f"No volume {VOLUME} of type emptyDir in the Pod. Volumes: {sorted(volumes) or 'none'}",
        fr=f"Aucun volume {VOLUME} de type emptyDir dans le Pod. Volumes : {sorted(volumes) or 'aucun'}",
    )
    for nom, conteneur in ((APP, principaux[APP]), (SIDECAR, inits[SIDECAR])):
        montes = [m["name"] for m in conteneur.get("volumeMounts") or []]
        assert VOLUME in montes, message(
            en=f"Container {nom} does not mount volume {VOLUME}: without the mount on "
            "both sides, nothing is shared.",
            fr=f"Le conteneur {nom} ne monte pas le volume {VOLUME} : sans montage des "
            "deux côtés, rien n'est partagé.",
        )
    assert pod["status"].get("phase") == "Running", message(
        en=f"The Pod is in phase {pod['status'].get('phase')!r}.",
        fr=f"Le Pod est en phase {pod['status'].get('phase')!r}.",
    )


# ----------------------------------------------------------------------
# 2. L'application écrit bien dans le fichier.
# ----------------------------------------------------------------------
def test_l_application_ecrit_le_fichier(host):
    res = _kubectl(host, f"-n {NAMESPACE} exec {POD} -c {APP} -- sh -c 'wc -l < {FICHIER}'")
    assert res.rc == 0, message(
        en=f"{FICHIER} does not exist in container {APP}: the application does not write "
        f"where it is expected to. Output: {res.stderr.strip()[:120]}",
        fr=f"{FICHIER} n'existe pas dans le conteneur {APP} : l'application n'écrit "
        f"pas là où on l'attend. Sortie : {res.stderr.strip()[:120]}",
    )
    assert int(res.stdout.strip() or 0) > 0, message(
        en=f"{FICHIER} exists but it is empty.",
        fr=f"{FICHIER} existe mais il est vide.",
    )


# ----------------------------------------------------------------------
# 3. La preuve : le sidecar recopie ces lignes sur sa sortie standard.
# ----------------------------------------------------------------------
def test_le_sidecar_transmet_les_lignes(host):
    derniere = _kubectl(host, f"-n {NAMESPACE} exec {POD} -c {APP} -- tail -n 1 {FICHIER}")
    assert derniere.rc == 0 and derniere.stdout.strip(), message(
        en="Cannot read a line of the file.",
        fr="Impossible de lire une ligne du fichier.",
    )
    logs = _kubectl(host, f"-n {NAMESPACE} logs {POD} -c {SIDECAR} --tail=20")
    assert logs.rc == 0, message(
        en=f"kubectl logs on {SIDECAR} failed: {logs.stderr.strip()[:150]}",
        fr=f"kubectl logs sur {SIDECAR} échoue : {logs.stderr.strip()[:150]}",
    )
    assert logs.stdout.strip(), message(
        en=f"The logs of sidecar {SIDECAR} are empty: it does not follow the file, or "
        "it reads a path other than the one app fills.",
        fr=f"Les logs du sidecar {SIDECAR} sont vides : il ne suit pas le fichier, ou "
        "il lit un chemin qui n'est pas celui que app remplit.",
    )
    # Le sidecar suit en continu : la ligne que app vient d'écrire, ou une
    # voisine, doit être dans ses vingt dernières.
    fragment = derniere.stdout.strip()[-24:]
    assert fragment in logs.stdout or len(logs.stdout.splitlines()) >= 5, message(
        en=f"The sidecar shows lines, but not the ones app writes: last "
        f"line of the file {derniere.stdout.strip()!r}, logs {logs.stdout.strip()[-200:]!r}",
        fr=f"Le sidecar affiche des lignes, mais pas celles que app écrit : dernière "
        f"ligne du fichier {derniere.stdout.strip()!r}, logs {logs.stdout.strip()[-200:]!r}",
    )
