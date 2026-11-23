"""test_functional.py : k8s-valider-et-modifier-a-l-admission

Trois affirmations, chacune prouvée par une vraie soumission à l'API server.
Les soumissions passent en ``--dry-run=server`` : la requête traverse toute
l'admission (webhooks, MutatingAdmissionPolicy, ValidatingAdmissionPolicy),
mais rien n'est écrit dans etcd. Un test ne laisse donc aucun Pod derrière lui.

Aucun des trois n'est vrai avant le travail, et c'est vérifié : au départ, le
webhook controle-ateliers refuse TOUT Pod d'ateliers en « failed calling
webhook », si bien qu'aucune soumission n'y aboutit et qu'aucun refus n'y vient
d'une politique.
"""

from __future__ import annotations

import json
import shlex
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "ateliers"
TEMOIN = "ateliers-temoin"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
IMAGE = "busybox:1.37"

# L'API server recharge politiques et webhooks après notification : ils
# n'agissent pas à la seconde où l'objet est accepté. Budget borné, pour ne pas
# recaler un candidat dont la correction est juste.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _pod(nom: str, privilegie: bool = False, init_privilegie: bool = False) -> dict:
    """Un Pod minimal, sans aucun label."""
    conteneur = {"name": "c", "image": IMAGE, "command": ["sleep", "60"]}
    if privilegie:
        conteneur["securityContext"] = {"privileged": True}
    spec: dict = {"restartPolicy": "Never", "containers": [conteneur]}
    if init_privilegie:
        spec["initContainers"] = [
            {
                "name": "prepa",
                "image": IMAGE,
                "command": ["true"],
                "securityContext": {"privileged": True},
            }
        ]
    return {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": nom}, "spec": spec}


def _soumettre(host, namespace: str, pod: dict):
    """Soumet le Pod en dry-run serveur. Rend (code, objet admis ou {}, message)."""
    manifeste = shlex.quote(json.dumps(pod))
    res = host.run(
        f"echo {manifeste} | sudo {KUBECTL} -n {namespace} create "
        "--dry-run=server -o json -f -"
    )
    objet: dict = {}
    if res.rc == 0:
        try:
            objet = json.loads(res.stdout)
        except json.JSONDecodeError:
            objet = {}
    # L'avertissement de ssh sur la clé d'hôte n'a rien à faire dans un message
    # que l'apprenant lit.
    diagnostic = "\n".join(
        ligne for ligne in res.stderr.splitlines()
        if not ligne.startswith("Warning: Permanently added")
    )
    return res.rc, objet, (diagnostic + res.stdout).strip()


def _attendre(host, namespace: str, pod: dict, condition):
    """Resoumet jusqu'à ce que la condition tienne, dans le budget. Rend le dernier essai."""
    fin = time.monotonic() + BUDGET_S
    essai = _soumettre(host, namespace, pod)
    while not condition(essai) and time.monotonic() < fin:
        time.sleep(PAS_S)
        essai = _soumettre(host, namespace, pod)
    return essai


# ----------------------------------------------------------------------
# 1. Le webhook orphelin ne bloque plus ateliers.
# ----------------------------------------------------------------------
def test_le_webhook_orphelin_ne_bloque_plus_ateliers(host):
    res = host.run(f"sudo {KUBECTL} get validatingwebhookconfiguration controle-ateliers -o name")
    assert res.rc != 0, message(
        en="The webhook configuration controle-ateliers is still there. It calls the "
        "Service verificateur of ateliers-outils, which has no Pod behind it: the "
        "controller was uninstalled, its configuration stayed. Remove it.",
        fr="La configuration de webhook controle-ateliers est toujours là. Elle "
        "appelle le Service verificateur d'ateliers-outils, qui n'a aucun Pod "
        "derrière lui : le contrôleur a été désinstallé, sa configuration est "
        "restée. Supprimez-la.",
    )

    rc, _, diagnostic = _attendre(host, NAMESPACE, _pod("sonde-simple"), lambda e: e[0] == 0)
    assert rc == 0, message(
        en=f"An ordinary Pod, not privileged, is still refused in {NAMESPACE}: "
        f"{diagnostic}",
        fr=f"Un Pod ordinaire, non privilégié, est toujours refusé dans "
        f"{NAMESPACE} : {diagnostic}",
    )


# ----------------------------------------------------------------------
# 2. Le label equipe est posé par défaut, dans ateliers seulement.
# ----------------------------------------------------------------------
def test_le_label_equipe_est_pose_dans_ateliers_seulement(host):
    def _labels(essai) -> dict:
        return (essai[1].get("metadata") or {}).get("labels") or {}

    essai = _attendre(
        host, NAMESPACE, _pod("sonde-label"),
        lambda e: e[0] == 0 and _labels(e).get("equipe") == "ateliers",
    )
    rc, _, diagnostic = essai
    assert rc == 0, message(
        en=f"An ordinary Pod is refused in {NAMESPACE}, so its labels cannot be "
        f"read: {diagnostic}",
        fr=f"Un Pod ordinaire est refusé dans {NAMESPACE}, ses labels ne peuvent "
        f"donc pas être lus : {diagnostic}",
    )
    labels = _labels(essai)
    assert labels.get("equipe") == "ateliers", message(
        en=f"A Pod submitted to {NAMESPACE} without any label comes out of "
        f"admission with the labels {labels}: the label equipe=ateliers is "
        "missing. It must be added by the API server itself, by a mutation "
        "bound to this namespace.",
        fr=f"Un Pod soumis à {NAMESPACE} sans aucun label sort de l'admission "
        f"avec les labels {labels} : le label equipe=ateliers manque. C'est "
        "l'API server lui-même qui doit l'ajouter, par une mutation liée à ce "
        "namespace.",
    )

    rc, objet, diagnostic = _soumettre(host, TEMOIN, _pod("sonde-label"))
    labels_temoin = (objet.get("metadata") or {}).get("labels") or {}
    assert rc == 0 and "equipe" not in labels_temoin, message(
        en=f"In {TEMOIN}, a Pod without labels comes out with {labels_temoin} "
        f"(code {rc}, {diagnostic}). The mutation must only apply to "
        f"{NAMESPACE}.",
        fr=f"Dans {TEMOIN}, un Pod sans label en sort avec {labels_temoin} "
        f"(code {rc}, {diagnostic}). La mutation ne doit s'appliquer qu'à "
        f"{NAMESPACE}.",
    )


# ----------------------------------------------------------------------
# 3. LE test : un Pod privilégié est refusé par une politique, et seulement là.
# ----------------------------------------------------------------------
def test_un_pod_privilegie_est_refuse_par_une_politique_dans_ateliers_seulement(host):
    """Preuve ACTIVE, dans les deux sens et sur les deux namespaces.

    Le refus doit venir d'une ValidatingAdmissionPolicy : au départ, le webhook
    orphelin refuse aussi le Pod privilégié, mais en « failed calling webhook »,
    ce qui ne prouve rien. Un conteneur d'initialisation privilégié a les mêmes
    accès au nœud qu'un conteneur ordinaire : il est refusé lui aussi.
    """
    def _refus_par_politique(essai) -> bool:
        return essai[0] != 0 and "validatingadmissionpolicy" in essai[2].lower()

    rc, _, refus = _attendre(
        host, NAMESPACE, _pod("sonde-privilegiee", privilegie=True), _refus_par_politique
    )
    assert _refus_par_politique((rc, {}, refus)), message(
        en=f"After {BUDGET_S} seconds, a privileged Pod is not refused by an "
        f"admission policy in {NAMESPACE} (code {rc}): {refus}",
        fr=f"Après {BUDGET_S} secondes, un Pod privilégié n'est pas refusé par "
        f"une politique d'admission dans {NAMESPACE} (code {rc}) : {refus}",
    )

    rc, _, refus = _soumettre(
        host, NAMESPACE, _pod("sonde-init-privilegiee", init_privilegie=True)
    )
    assert _refus_par_politique((rc, {}, refus)), message(
        en=f"A Pod whose INIT container is privileged goes through in "
        f"{NAMESPACE} (code {rc}): {refus}. An init container in privileged "
        "mode gets the same access to the node as an ordinary container: the "
        "rule must look at both lists.",
        fr=f"Un Pod dont le conteneur d'INITIALISATION est privilégié passe dans "
        f"{NAMESPACE} (code {rc}) : {refus}. Un conteneur d'initialisation en "
        "mode privileged a les mêmes accès au nœud qu'un conteneur ordinaire : "
        "la règle doit regarder les deux listes.",
    )

    rc, _, diagnostic = _soumettre(host, NAMESPACE, _pod("sonde-ordinaire"))
    assert rc == 0, message(
        en=f"An ordinary Pod is refused too in {NAMESPACE}: {diagnostic}. The "
        "rule must refuse privileged Pods, not every Pod.",
        fr=f"Un Pod ordinaire est refusé lui aussi dans {NAMESPACE} : "
        f"{diagnostic}. La règle doit refuser les Pods privilégiés, pas tous "
        "les Pods.",
    )

    rc, _, diagnostic = _soumettre(host, TEMOIN, _pod("sonde-privilegiee", privilegie=True))
    assert rc == 0, message(
        en=f"A privileged Pod is refused in {TEMOIN}: {diagnostic}. The rule "
        f"must only apply to {NAMESPACE}.",
        fr=f"Un Pod privilégié est refusé dans {TEMOIN} : {diagnostic}. La règle "
        f"ne doit s'appliquer qu'à {NAMESPACE}.",
    )
