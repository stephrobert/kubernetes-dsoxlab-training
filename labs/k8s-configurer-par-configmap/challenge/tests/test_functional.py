"""test_functional.py : k8s-configurer-par-configmap

Ces tests lisent les ConfigMaps app-config et app-fichier, le Deployment app,
et ce que voit son conteneur (printenv, cat), lu DANS le Pod. Un test vérifie
un seul état demandé par l'énoncé.

Les valeurs attendues sont celles d'après la modification : LOG_LEVEL à debug,
app.properties en mode=maintenance. Le fichier monté en dossier se met à jour
seul, avec un délai ; les variables ne suivent qu'au remplacement du Pod, d'où
l'exigence du rollout restart, lue dans l'annotation qu'il pose sur le modèle.

Aucun test n'attend tant que le travail n'est pas commencé : l'attente du
rafraîchissement ne s'ouvre que si le volume est déjà monté comme demandé.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "configuration"
MONTAGE = "/etc/app"
RESTART = "kubectl.kubernetes.io/restartedAt"
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _app(host) -> dict:
    dep = _json(host, "get deployment app")
    assert dep is not None, message(
        en=f"No Deployment app in the {NS} namespace.",
        fr=f"Aucun Deployment app dans le namespace {NS}.",
    )
    return dep


def _donnees(host, nom: str) -> dict:
    cm = _json(host, f"get configmap {nom}")
    assert cm is not None, message(
        en=f"No ConfigMap {nom} in the {NS} namespace.",
        fr=f"Aucun ConfigMap {nom} dans le namespace {NS}.",
    )
    return cm.get("data") or {}


def _conteneur(dep: dict) -> dict:
    return (dep["spec"]["template"]["spec"].get("containers") or [{}])[0]


def _pod_vivant(host) -> str:
    """Un Pod prêt de app, hors Pods en cours de suppression : après un rollout
    restart, l'ancien Pod reste en Terminating pendant son délai de grâce (sleep
    ignore SIGTERM), et `exec deploy/app` pourrait encore le choisir."""
    dep = _json(host, "get deployment app") or {}
    etiquettes = ((dep.get("spec") or {}).get("selector") or {}).get("matchLabels") or {}
    if not etiquettes:
        return ""
    selecteur = ",".join(f"{k}={v}" for k, v in sorted(etiquettes.items()))
    pods = (_json(host, f"get pods -l {selecteur}") or {}).get("items") or []
    vivants = [
        p for p in pods
        if not p["metadata"].get("deletionTimestamp")
        and all(s.get("ready") for s in (p.get("status") or {}).get("containerStatuses") or [{}])
    ]
    vivants.sort(key=lambda p: p["metadata"]["creationTimestamp"], reverse=True)
    return vivants[0]["metadata"]["name"] if vivants else ""


def _dans_le_pod(host, commande: str) -> str:
    pod = _pod_vivant(host)
    if not pod:
        return ""
    res = host.run(f"{ADMIN} -n {NS} exec {pod} -- {commande}")
    return res.stdout.strip() if res.rc == 0 else ""


def _vient_de_app_config(conteneur: dict, variable: str) -> bool:
    for e in conteneur.get("env") or []:
        if e.get("name") == variable:
            ref = (e.get("valueFrom") or {}).get("configMapKeyRef") or {}
            return ref.get("name") == "app-config"
    return any((src.get("configMapRef") or {}).get("name") == "app-config"
               for src in conteneur.get("envFrom") or [])


def _normal(texte: str) -> str:
    return "\n".join(ligne.strip() for ligne in texte.strip().splitlines() if ligne.strip())


# ----------------------------------------------------------------------
# 1. Les variables viennent de app-config.
# ----------------------------------------------------------------------
def test_les_variables_viennent_du_configmap_app_config(host):
    donnees = _donnees(host, "app-config")
    conteneur = _conteneur(_app(host))
    for variable in ("APP_MODE", "LOG_LEVEL"):
        assert _vient_de_app_config(conteneur, variable), message(
            en=f"{variable} does not come from the app-config ConfigMap in the Deployment: "
            "envFrom with configMapRef gives one variable per key.",
            fr=f"{variable} ne vient pas du ConfigMap app-config dans le Deployment : envFrom "
            "avec configMapRef donne une variable par clé.",
        )
    vue = _dans_le_pod(host, "printenv APP_MODE")
    assert vue and vue == donnees.get("APP_MODE"), message(
        en=f"Inside the Pod, APP_MODE is {vue!r}; app-config says {donnees.get('APP_MODE')!r}.",
        fr=f"Dans le Pod, APP_MODE vaut {vue!r} ; app-config dit {donnees.get('APP_MODE')!r}.",
    )


# ----------------------------------------------------------------------
# 2. Le fichier monté depuis app-fichier, à jour.
# ----------------------------------------------------------------------
def test_le_fichier_monte_depuis_app_fichier_est_a_jour(host):
    attendu = _donnees(host, "app-fichier").get("app.properties", "")
    assert "mode=maintenance" in attendu, message(
        en="The key app.properties of app-fichier does not say mode=maintenance yet: the "
        "change of the file is part of the work.",
        fr="La clé app.properties de app-fichier ne dit pas encore mode=maintenance : la "
        "modification du fichier fait partie du travail.",
    )
    dep = _app(host)
    volumes = {v.get("name"): (v.get("configMap") or {}).get("name")
               for v in dep["spec"]["template"]["spec"].get("volumes") or []}
    montages = [m for m in _conteneur(dep).get("volumeMounts") or []
                if volumes.get(m.get("name")) == "app-fichier" and m.get("mountPath") == MONTAGE]
    assert montages and not montages[0].get("subPath"), message(
        en=f"The app-fichier ConfigMap is not mounted as a directory on {MONTAGE}. A subPath "
        "mount is never refreshed: mount the volume as a directory.",
        fr=f"Le ConfigMap app-fichier n'est pas monté en dossier sur {MONTAGE}. Un montage par "
        "subPath n'est jamais rafraîchi : montez le volume en dossier.",
    )
    # Le montage est juste : le kubelet rafraîchit le dossier avec un délai.
    fin = time.monotonic() + ATTENTE
    vu = _dans_le_pod(host, f"cat {MONTAGE}/app.properties")
    while _normal(vu) != _normal(attendu) and time.monotonic() < fin:
        time.sleep(PAS)
        vu = _dans_le_pod(host, f"cat {MONTAGE}/app.properties")
    assert _normal(vu) == _normal(attendu), message(
        en=f"Inside the Pod, {MONTAGE}/app.properties says {vu!r} after {ATTENTE}s, whereas "
        f"app-fichier says {attendu!r}.",
        fr=f"Dans le Pod, {MONTAGE}/app.properties dit {vu!r} après {ATTENTE}s, alors que "
        f"app-fichier dit {attendu!r}.",
    )


# ----------------------------------------------------------------------
# 3. Le rollout restart a rafraîchi les variables.
# ----------------------------------------------------------------------
def test_le_rollout_restart_a_rafraichi_les_variables(host):
    donnees = _donnees(host, "app-config")
    assert donnees.get("LOG_LEVEL") == "debug", message(
        en=f"LOG_LEVEL is {donnees.get('LOG_LEVEL')!r} in app-config: change it to debug.",
        fr=f"LOG_LEVEL vaut {donnees.get('LOG_LEVEL')!r} dans app-config : passez-le à debug.",
    )
    dep = _app(host)
    annotations = dep["spec"]["template"]["metadata"].get("annotations") or {}
    assert RESTART in annotations, message(
        en="The Deployment app was not restarted after the change: an environment variable is "
        "read once, when the container starts. kubectl rollout restart replaces the Pods. "
        "Reread the section of the lesson on what is refreshed and what is not.",
        fr="Le Deployment app n'a pas été redémarré après la modification : une variable "
        "d'environnement se lit une fois, au démarrage du conteneur. kubectl rollout restart "
        "remplace les Pods. Relisez la section de la leçon sur ce qui se rafraîchit et ce qui "
        "ne se rafraîchit pas.",
    )
    vue = _dans_le_pod(host, "printenv LOG_LEVEL")
    assert vue == "debug", message(
        en=f"Inside the Pod, LOG_LEVEL is {vue!r}, expected 'debug': the restart must come "
        "AFTER the change of app-config.",
        fr=f"Dans le Pod, LOG_LEVEL vaut {vue!r}, attendu 'debug' : le redémarrage doit venir "
        "APRÈS la modification de app-config.",
    )


# ----------------------------------------------------------------------
# 4. Aucune valeur écrite en dur.
# ----------------------------------------------------------------------
def test_aucune_valeur_n_est_ecrite_en_dur_dans_le_deployment(host):
    en_dur = [e.get("name") for c in _app(host)["spec"]["template"]["spec"].get("containers") or []
              for e in c.get("env") or [] if "value" in e]
    assert not en_dur, message(
        en=f"Values are written directly in the Deployment: {en_dur}. They belong in the "
        "ConfigMap, which the Deployment references.",
        fr=f"Des valeurs sont écrites directement dans le Deployment : {en_dur}. Elles vont dans "
        "le ConfigMap, que le Deployment référence.",
    )
