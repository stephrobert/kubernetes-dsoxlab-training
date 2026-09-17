"""test_functional.py : cks-validating-admission-policy

Deux affirmations, et la seconde est une preuve ACTIVE dans les deux sens :
le test crée réellement les deux Pods, l'un par tag et l'autre par digest, et
constate le refus du premier et l'acceptation du second.

Relire la politique ne prouverait rien. Une ValidatingAdmissionPolicy sans
ValidatingAdmissionPolicyBinding est un objet parfaitement valide qui n'agit
sur rien ; une liaison dont `validationActions` vaut `Warn` signale sans
refuser ; une expression CEL avec `exists` au lieu de `all` laisse passer un
Pod dont un seul conteneur sur deux est épinglé.

Les Pods sondes sont supprimés après usage : un test ne laisse pas de trace.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "production"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
IMAGE_TAG = "busybox:1.37"
IMAGE_DIGEST = "busybox@sha256:ab33eacc8251e3807b85bb6dba570e4698c3998eca6f0fc2ccb60575a563ea74"

# L'API server recharge ses politiques après notification : elles n'agissent
# pas à la seconde où l'objet est accepté. Budget borné, pour ne pas recaler un
# candidat dont la correction est juste.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _supprimer(host, pod: str) -> None:
    """Supprime une sonde et ATTEND sa disparition.

    L'attente n'est pas du zèle : une suppression lancée sans attendre laisse le
    Pod en cours de suppression, et la tentative suivante se heurte à « object
    is being deleted: pods … already exists ». Le test échouerait alors pour une
    course, et non pour ce qu'il mesure. Ce lab y est d'autant plus exposé que
    sa sonde est recréée en boucle jusqu'à ce que la politique agisse.
    """
    _kubectl(
        host,
        f"-n {NAMESPACE} delete pod {pod} --ignore-not-found "
        "--wait=true --timeout=90s",
    )


def _tenter(host, nom: str, image: str):
    """Crée un Pod sonde et rend (code, message). Le Pod est supprimé."""
    _supprimer(host, nom)
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} run {nom} --image={image} --restart=Never "
        "--command -- sh -c 'sleep 30'",
    )
    _supprimer(host, nom)
    return rc, (diagnostic + sortie)


# ----------------------------------------------------------------------
# 1. Une politique existe, et elle est LIÉE en mode refus.
# ----------------------------------------------------------------------
def test_une_politique_est_liee_en_mode_refus(host):
    """Ce test ne prouve rien à lui seul, et c'est voulu : il est là pour que
    l'échec du test suivant soit diagnosticable, et pour nommer laquelle des
    deux moitiés manque."""
    rc, sortie, diagnostic = _kubectl(host, "get validatingadmissionpolicy -o json")
    assert rc == 0, f"Impossible de lire les politiques d'admission. {diagnostic}"
    politiques = [
        p["metadata"]["name"]
        for p in json.loads(sortie or "{}").get("items", [])
        if not p["metadata"]["name"].startswith("safe-upgrades")
    ]
    assert politiques, (
        "Aucune ValidatingAdmissionPolicy dans le cluster. C'est l'objet par "
        "lequel l'API server évalue lui-même une règle, sans webhook ni "
        "contrôleur à maintenir en vie."
    )

    rc, sortie, diagnostic = _kubectl(
        host, "get validatingadmissionpolicybinding -o json"
    )
    assert rc == 0, f"Impossible de lire les liaisons. {diagnostic}"
    liaisons = [
        b for b in json.loads(sortie or "{}").get("items", [])
        if b["spec"].get("policyName") in politiques
    ]
    assert liaisons, (
        f"La ou les politiques {politiques} ne sont liées à rien. Une "
        "politique SANS liaison est un objet parfaitement valide qui n'agit "
        "sur aucune requête : c'est la liaison qui dit OÙ elle s'applique, et "
        "ce qu'on fait des violations."
    )

    actions = {
        b["metadata"]["name"]: b["spec"].get("validationActions")
        for b in liaisons
    }
    assert any(
        "Deny" in (b["spec"].get("validationActions") or []) for b in liaisons
    ), (
        f"Aucune liaison ne refuse : {actions}. « Warn » prévient celui qui "
        "applique et « Audit » laisse une trace, mais tous deux LAISSENT "
        "PASSER. Seul « Deny » refuse."
    )


# ----------------------------------------------------------------------
# 2. LE test : le tag est refusé, le digest passe.
# ----------------------------------------------------------------------
def test_une_image_par_tag_est_refusee_et_une_image_epinglee_passe(host):
    """Preuve ACTIVE, et dans les deux sens.

    Les deux mesures sont dans le MÊME test, délibérément. « Une image épinglée
    passe » est déjà vrai AVANT le travail, puisque rien ne refuse quoi que ce
    soit : isolée, cette assertion ferait un test vert qui ne mesure rien.
    Accolée à l'autre, elle prend tout son sens : elle distingue une politique
    qui vise juste d'une politique qui refuse tout.

    Mesuré le 2026-09-17 : le refus porte le message de la politique elle-même,
    « ValidatingAdmissionPolicy '<nom>' with binding '<nom>' denied request:
    … ».
    """
    fin = time.monotonic() + BUDGET_S
    rc_tag, message = 0, ""
    while time.monotonic() < fin:
        rc_tag, message = _tenter(host, "sonde-tag", IMAGE_TAG)
        if rc_tag != 0:
            break
        time.sleep(PAS_S)

    assert rc_tag != 0, (
        f"Après {BUDGET_S} secondes, le namespace {NAMESPACE} accepte "
        f"toujours l'image « {IMAGE_TAG} », qui n'est pas épinglée. Un tag "
        "peut être redirigé vers un autre contenu sans que rien ne change "
        "dans le manifeste : c'est exactement ce que la politique devait "
        "empêcher. Vérifiez que la liaison désigne bien ce namespace."
    )
    assert "denied request" in message.lower() or "validatingadmissionpolicy" in message.lower(), (
        "Le Pod a bien été refusé, mais pas par une politique d'admission. Le "
        f"message était : {message}"
    )

    rc_digest, message_digest = _tenter(host, "sonde-digest", IMAGE_DIGEST)
    assert rc_digest == 0, (
        f"L'image épinglée « {IMAGE_DIGEST} » est refusée elle aussi : "
        f"{message_digest}. La politique refuse donc tout, ce qui n'est pas "
        "ce qu'on vous demandait : elle doit distinguer une image épinglée "
        "d'une image par tag, et non bloquer le namespace."
    )

    rc, phase, _ = _kubectl(
        host, f"-n {NAMESPACE} get pod conforme -o jsonpath='{{.status.phase}}'"
    )
    assert rc == 0 and phase == "Running", (
        f"Le Pod conforme, posé par le setup avec une image épinglée, est en "
        f"« {phase or 'absent'} ». Une politique ne juge qu'à la CRÉATION : un "
        "Pod déjà là ne peut pas avoir été refusé, il a donc été supprimé ou "
        "n'a jamais démarré."
    )
