"""test_functional.py : k8s-configurer-par-configmap

Ces tests lisent les ConfigMaps tarifs-env et tarifs-grille, le Deployment tarifs,
et ce que voit son conteneur (printenv, cat), lu DANS le Pod. Un test vérifie
un seul état demandé par l'énoncé.

Les valeurs attendues sont celles d'après la modification : TAUX_TVA à 5.5,
grille.ini en remise=15. Le fichier monté en dossier se met à jour
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
NS = "tarification"
MONTAGE = "/etc/tarifs"
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
    dep = _json(host, "get deployment tarifs")
    assert dep is not None, message(
        en=f"No Deployment tarifs in the {NS} namespace.",
        fr=f"Aucun Deployment tarifs dans le namespace {NS}.",
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
    """Un Pod prêt de tarifs, hors Pods en cours de suppression : après un rollout
    restart, l'ancien Pod reste en Terminating pendant son délai de grâce (sleep
    ignore SIGTERM), et `exec deploy/tarifs` pourrait encore le choisir."""
    dep = _json(host, "get deployment tarifs") or {}
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


def _vient_de_tarifs_env(conteneur: dict, variable: str) -> bool:
    for e in conteneur.get("env") or []:
        if e.get("name") == variable:
            ref = (e.get("valueFrom") or {}).get("configMapKeyRef") or {}
            return ref.get("name") == "tarifs-env"
    return any((src.get("configMapRef") or {}).get("name") == "tarifs-env"
               for src in conteneur.get("envFrom") or [])


def _normal(texte: str) -> str:
    return "\n".join(ligne.strip() for ligne in texte.strip().splitlines() if ligne.strip())


# ----------------------------------------------------------------------
# 1. Les variables viennent de tarifs-env.
# ----------------------------------------------------------------------
def test_les_variables_viennent_du_configmap_tarifs_env(host):
    donnees = _donnees(host, "tarifs-env")
    conteneur = _conteneur(_app(host))
    for variable in ("DEVISE", "TAUX_TVA"):
        assert _vient_de_tarifs_env(conteneur, variable), message(
            en=f"{variable} does not come from the tarifs-env ConfigMap in the Deployment: "
            "envFrom with configMapRef gives one variable per key.",
            fr=f"{variable} ne vient pas du ConfigMap tarifs-env dans le Deployment : envFrom "
            "avec configMapRef donne une variable par clé.",
        )
    vue = _dans_le_pod(host, "printenv DEVISE")
    assert vue and vue == donnees.get("DEVISE"), message(
        en=f"Inside the Pod, DEVISE is {vue!r}; tarifs-env says {donnees.get('DEVISE')!r}.",
        fr=f"Dans le Pod, DEVISE vaut {vue!r} ; tarifs-env dit {donnees.get('DEVISE')!r}.",
    )


# ----------------------------------------------------------------------
# 2. Le fichier monté depuis tarifs-grille, à jour.
# ----------------------------------------------------------------------
def test_le_fichier_monte_depuis_tarifs_grille_est_a_jour(host):
    attendu = _donnees(host, "tarifs-grille").get("grille.ini", "")
    assert "remise=15" in attendu, message(
        en="The key grille.ini of tarifs-grille does not say remise=15 yet: the "
        "change of the file is part of the work.",
        fr="La clé grille.ini de tarifs-grille ne dit pas encore remise=15 : la "
        "modification du fichier fait partie du travail.",
    )
    dep = _app(host)
    volumes = {v.get("name"): (v.get("configMap") or {}).get("name")
               for v in dep["spec"]["template"]["spec"].get("volumes") or []}
    montages = [m for m in _conteneur(dep).get("volumeMounts") or []
                if volumes.get(m.get("name")) == "tarifs-grille" and m.get("mountPath") == MONTAGE]
    assert montages and not montages[0].get("subPath"), message(
        en=f"The tarifs-grille ConfigMap is not mounted as a directory on {MONTAGE}. A subPath "
        "mount is never refreshed: mount the volume as a directory.",
        fr=f"Le ConfigMap tarifs-grille n'est pas monté en dossier sur {MONTAGE}. Un montage par "
        "subPath n'est jamais rafraîchi : montez le volume en dossier.",
    )
    # Le montage est juste : le kubelet rafraîchit le dossier avec un délai.
    fin = time.monotonic() + ATTENTE
    vu = _dans_le_pod(host, f"cat {MONTAGE}/grille.ini")
    while _normal(vu) != _normal(attendu) and time.monotonic() < fin:
        time.sleep(PAS)
        vu = _dans_le_pod(host, f"cat {MONTAGE}/grille.ini")
    assert _normal(vu) == _normal(attendu), message(
        en=f"Inside the Pod, {MONTAGE}/grille.ini says {vu!r} after {ATTENTE}s, whereas "
        f"tarifs-grille says {attendu!r}.",
        fr=f"Dans le Pod, {MONTAGE}/grille.ini dit {vu!r} après {ATTENTE}s, alors que "
        f"tarifs-grille dit {attendu!r}.",
    )


# ----------------------------------------------------------------------
# 3. Le rollout restart a rafraîchi les variables.
# ----------------------------------------------------------------------
def test_le_rollout_restart_a_rafraichi_les_variables(host):
    donnees = _donnees(host, "tarifs-env")
    assert donnees.get("TAUX_TVA") == "5.5", message(
        en=f"TAUX_TVA is {donnees.get('TAUX_TVA')!r} in tarifs-env: change it to 5.5.",
        fr=f"TAUX_TVA vaut {donnees.get('TAUX_TVA')!r} dans tarifs-env : passez-le à 5.5.",
    )
    dep = _app(host)
    annotations = dep["spec"]["template"]["metadata"].get("annotations") or {}
    assert RESTART in annotations, message(
        en="The Deployment tarifs was not restarted after the change: an environment variable is "
        "read once, when the container starts. kubectl rollout restart replaces the Pods. "
        "Reread the section of the lesson on what is refreshed and what is not.",
        fr="Le Deployment tarifs n'a pas été redémarré après la modification : une variable "
        "d'environnement se lit une fois, au démarrage du conteneur. kubectl rollout restart "
        "remplace les Pods. Relisez la section de la leçon sur ce qui se rafraîchit et ce qui "
        "ne se rafraîchit pas.",
    )
    vue = _dans_le_pod(host, "printenv TAUX_TVA")
    assert vue == "5.5", message(
        en=f"Inside the Pod, TAUX_TVA is {vue!r}, expected '5.5': the restart must come "
        "AFTER the change of tarifs-env.",
        fr=f"Dans le Pod, TAUX_TVA vaut {vue!r}, attendu '5.5' : le redémarrage doit venir "
        "APRÈS la modification de tarifs-env.",
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
