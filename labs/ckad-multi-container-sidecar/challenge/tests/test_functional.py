"""test_functional.py : ckad-multi-container-sidecar

Ces tests lisent la définition du Pod app-with-sidecar, le fichier que
l'application écrit, puis les logs du sidecar. Un test vérifie un seul état
demandé par l'énoncé.

Tous échouent avant le travail : le Pod n'existe pas. L'attente du Pod Running
ne s'ouvre que s'il existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
POD = "app-with-sidecar"
APP = "app"
SIDECAR = "log-shipper"
VOLUME = "logs"
FICHIER = "/var/log/app/output.log"
IMAGE = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 90
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(host) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} get pod {POD} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _pod_en_marche(host) -> dict | None:
    pod = _pod(host)
    fin = time.monotonic() + ATTENTE
    while pod is not None and pod["status"].get("phase") != "Running" and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _pod(host) or pod
    return pod


def _absent() -> str:
    return message(en=f"No Pod {POD} in {NS}.", fr=f"Aucun Pod {POD} dans {NS}.")


# ----------------------------------------------------------------------
# 1. log-shipper est un sidecar natif.
# ----------------------------------------------------------------------
def test_log_shipper_est_un_sidecar_natif(host):
    pod = _pod(host)
    assert pod is not None, _absent()
    inits = {c["name"]: c for c in pod["spec"].get("initContainers") or []}
    principaux = [c["name"] for c in pod["spec"]["containers"]]
    sidecar = inits.get(SIDECAR) or {}
    assert sidecar.get("restartPolicy") == "Always" and SIDECAR not in principaux \
            and sidecar.get("image") == IMAGE, message(
        en=f"{SIDECAR} is not a native sidecar on the image of the requirements (init containers: "
        f"{sorted(inits) or 'none'}, main containers: {principaux}). A second ordinary container is not "
        "a native sidecar: it starts at the same time as the application and is not stopped after it.",
        fr=f"{SIDECAR} n'est pas un sidecar natif sur l'image du cahier des charges (init containers : "
        f"{sorted(inits) or 'aucun'}, conteneurs principaux : {principaux}). Un second conteneur "
        "ordinaire n'est pas un sidecar natif : il démarre en même temps que l'application et n'est "
        "pas arrêté après elle.",
    )


# ----------------------------------------------------------------------
# 2. Le volume logs est partagé par les deux conteneurs.
# ----------------------------------------------------------------------
def test_le_volume_logs_est_partage_par_les_deux_conteneurs(host):
    pod = _pod(host)
    assert pod is not None, _absent()
    volumes = {v["name"]: v for v in pod["spec"].get("volumes") or []}
    tous = pod["spec"]["containers"] + (pod["spec"].get("initContainers") or [])
    sans = [c["name"] for c in tous if c["name"] in (APP, SIDECAR)
            and VOLUME not in [m["name"] for m in c.get("volumeMounts") or []]]
    presents = {c["name"] for c in tous} & {APP, SIDECAR}
    assert "emptyDir" in volumes.get(VOLUME, {}) and presents == {APP, SIDECAR} and not sans, message(
        en=f"The {VOLUME} emptyDir volume is not mounted in both {APP} and {SIDECAR} (containers "
        f"without it: {sans or 'none'}, volumes: {sorted(volumes) or 'none'}). Two containers share "
        "nothing by default, not even a directory.",
        fr=f"Le volume emptyDir {VOLUME} n'est pas monté à la fois dans {APP} et {SIDECAR} (conteneurs "
        f"qui ne l'ont pas : {sans or 'aucun'}, volumes : {sorted(volumes) or 'aucun'}). Deux conteneurs "
        "ne partagent rien par défaut, même pas un répertoire.",
    )


# ----------------------------------------------------------------------
# 3. app écrit dans le fichier partagé.
# ----------------------------------------------------------------------
def test_app_ecrit_dans_le_fichier_partage(host):
    pod = _pod_en_marche(host)
    assert pod is not None, _absent()
    image = {c["name"]: c.get("image") for c in pod["spec"]["containers"]}.get(APP)
    res = host.run(f"{ADMIN} -n {NS} exec {POD} -c {APP} -- sh -c 'wc -l < {FICHIER}'")
    lignes = int(res.stdout.strip() or 0) if res.rc == 0 else 0
    assert image == IMAGE and lignes > 0, message(
        en=f"{APP} runs {image!r} and {FICHIER} holds {lignes} line(s) in it. Expected the image of the "
        "requirements, and a file that fills up.",
        fr=f"{APP} tourne en {image!r} et {FICHIER} y compte {lignes} ligne(s). Attendu l'image du cahier "
        "des charges, et un fichier qui se remplit.",
    )


# ----------------------------------------------------------------------
# 4. Le sidecar transmet les lignes de l'application.
# ----------------------------------------------------------------------
def test_le_sidecar_transmet_les_lignes_de_l_application(host):
    pod = _pod_en_marche(host)
    assert pod is not None, _absent()
    derniere = host.run(f"{ADMIN} -n {NS} exec {POD} -c {APP} -- tail -n 1 {FICHIER}").stdout.strip()
    time.sleep(3)
    logs = host.run(f"{ADMIN} -n {NS} logs {POD} -c {SIDECAR} --tail=30")
    assert derniere and logs.rc == 0 and derniere in logs.stdout, message(
        en=f"The logs of {SIDECAR} do not show the lines {APP} writes (last line of the file: "
        f"{derniere or 'none'!r}). The sidecar must follow that very file, continuously.",
        fr=f"Les logs de {SIDECAR} ne montrent pas les lignes que {APP} écrit (dernière ligne du "
        f"fichier : {derniere or 'aucune'!r}). Le sidecar doit suivre ce fichier-là, en continu.",
    )
