"""test_functional.py — cks-apparmor-confiner-un-pod

Ces tests lisent l'état du NŒUD et du CLUSTER, jamais les commandes tapées.
C'est la seule façon de valider une compétence d'examen pratique : le candidat
peut arriver au résultat par le chemin qu'il veut, et seul le résultat compte.

Le dernier test est le seul qui prouve vraiment quelque chose. Un profil chargé
et un Pod qui le déclare ne démontrent pas que le confinement AGIT : on tente
donc une écriture réellement interdite, et on vérifie qu'elle échoue, pendant
qu'une lecture, elle, réussit. Sans ce contrôle en creux, un profil vide
passerait le lab.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host

PROFIL = "k8s-refuser-ecriture"
NAMESPACE = "confinement"
POD = "confine"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


# ----------------------------------------------------------------------
# 1. Le profil est chargé dans le noyau, et il est en enforce.
# ----------------------------------------------------------------------
def test_profil_charge_en_enforce(host):
    """Un fichier de profil posé sur le disque ne confine rien.

    `aa-status --json` sépare les modes : on exige `enforce`, parce qu'un
    profil en `complain` journalise les violations sans les empêcher. C'est
    la confusion la plus fréquente sur ce sujet, et elle coûte les points à
    l'examen comme en production.
    """
    res = host.run("sudo aa-status --json")
    assert res.rc == 0, f"aa-status a échoué : {res.stderr}"

    profils = json.loads(res.stdout).get("profiles", {})
    assert PROFIL in profils, (
        f"Le profil « {PROFIL} » n'est pas chargé dans le noyau. "
        f"Le fichier existe dans /etc/apparmor.d/, mais il faut le charger. "
        f"Profils connus : {sorted(profils)[:8]}"
    )
    assert profils[PROFIL] == "enforce", (
        f"Le profil « {PROFIL} » est en mode « {profils[PROFIL]} ». "
        "En « complain », les violations sont journalisées mais PAS bloquées : "
        "le conteneur écrirait quand même."
    )


# ----------------------------------------------------------------------
# 2. Le Pod existe et tourne.
# ----------------------------------------------------------------------
def test_pod_en_marche(host):
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o jsonpath='{{.status.phase}}'")
    assert res.rc == 0, (
        f"Le Pod « {POD} » est introuvable dans le namespace « {NAMESPACE} ». "
        f"Sortie : {res.stderr.strip()}"
    )
    assert res.stdout.strip() == "Running", (
        f"Le Pod « {POD} » est en phase « {res.stdout.strip()} » et non « Running ». "
        "Un Pod dont le profil AppArmor est introuvable reste bloqué : regardez "
        "ses events, le kubelet y nomme le profil qu'il n'a pas trouvé."
    )


# ----------------------------------------------------------------------
# 3. Le profil est déclaré dans le securityContext, pas par l'annotation.
# ----------------------------------------------------------------------
def test_profil_declare_dans_le_security_context(host):
    """Depuis Kubernetes 1.30, le rattachement se déclare en champ typé.

    L'annotation `container.apparmor.security.beta.kubernetes.io/<c>`
    fonctionne encore, mais elle est obsolète et l'examen attend la forme
    moderne. On refuse donc explicitement la vieille écriture, sans quoi le
    lab validerait une pratique qu'il est censé remplacer.
    """
    res = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert res.rc == 0, f"Lecture du Pod impossible : {res.stderr}"
    pod = json.loads(res.stdout)

    annotations = pod.get("metadata", {}).get("annotations", {}) or {}
    obsoletes = [c for c in annotations if "apparmor.security.beta.kubernetes.io" in c]
    assert not obsoletes, (
        "Le profil est rattaché par une ANNOTATION obsolète "
        f"({obsoletes[0]}). Depuis la 1.30, il se déclare dans "
        "securityContext.appArmorProfile."
    )

    profils_vus = []
    for niveau in (pod.get("spec", {}),):
        p = (niveau.get("securityContext") or {}).get("appArmorProfile")
        if p:
            profils_vus.append(p)
    for conteneur in pod.get("spec", {}).get("containers", []):
        p = (conteneur.get("securityContext") or {}).get("appArmorProfile")
        if p:
            profils_vus.append(p)

    assert profils_vus, (
        "Aucun appArmorProfile dans le securityContext, ni au niveau du Pod "
        "ni au niveau du conteneur."
    )

    localises = [p for p in profils_vus if p.get("type") == "Localhost"]
    assert localises, (
        "Le type du profil doit être « Localhost » pour désigner un profil "
        f"chargé sur le nœud. Vu : {[p.get('type') for p in profils_vus]}. "
        "« RuntimeDefault » applique le profil par défaut du runtime, pas le vôtre."
    )
    noms = [p.get("localhostProfile") for p in localises]
    assert PROFIL in noms, (
        f"Le profil désigné est {noms}, pas « {PROFIL} ». Attention : le nom "
        "attendu est celui écrit après « profile » DANS le fichier, pas le nom "
        "du fichier."
    )


# ----------------------------------------------------------------------
# 4. La seule preuve qui compte : le confinement agit.
# ----------------------------------------------------------------------
def test_ecriture_refusee_et_lecture_permise(host):
    """Un profil qui n'interdit rien passerait les trois tests précédents.

    On exerce donc les deux côtés : ce que le profil refuse doit échouer, et
    ce qu'il autorise doit réussir. Un conteneur mort ferait échouer les deux,
    d'où le second contrôle.
    """
    ecriture = _kubectl(
        host,
        f"-n {NAMESPACE} exec {POD} -- sh -c "
        "'echo test > /tmp/preuve-apparmor 2>&1; echo CODE=$?'",
    )
    assert "CODE=0" not in ecriture.stdout, (
        "L'écriture dans /tmp a RÉUSSI : le conteneur n'est pas confiné par "
        f"le profil attendu. Sortie : {ecriture.stdout.strip()}"
    )

    lecture = _kubectl(
        host, f"-n {NAMESPACE} exec {POD} -- sh -c 'cat /etc/hostname >/dev/null; echo CODE=$?'"
    )
    assert "CODE=0" in lecture.stdout, (
        "La lecture de /etc/hostname échoue aussi : le profil est trop "
        "restrictif, ou le conteneur ne tourne pas. Un confinement qui casse "
        "l'application ne vaut pas mieux qu'une absence de confinement. "
        f"Sortie : {lecture.stdout.strip()}"
    )
