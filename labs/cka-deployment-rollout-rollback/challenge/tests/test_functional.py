"""test_functional.py : cka-deployment-rollout-rollback

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première veut le Deployment sain sur la bonne image.
La deuxième lit les ReplicaSets et leurs numéros de révision : celui de la
version d'avant doit avoir été réactivé après la révision fautive, c'est la
trace d'un retour arrière, et un candidat qui aurait sauté cette étape n'en
laisse pas. La troisième veut le ReplicaSet fautif encore là, à zéro : un
historique se garde, il ne se supprime pas. La quatrième lit la cause de
changement sur la révision finale.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
DEPLOYMENT = "webapp"
IMAGE_AVANT = "nginx:1.26-alpine"
IMAGE_FAUTIVE = "nginx:1.27-alpin"
IMAGE = "nginx:1.27-alpine"
REVISION = "deployment.kubernetes.io/revision"
CAUSE = "kubernetes.io/change-cause"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str) -> dict:
    res = _kubectl(host, args + " -o json")
    assert res.rc == 0, f"kubectl {args} échoue : {res.stderr.strip()[:200]}"
    return json.loads(res.stdout)


def _replicasets(host) -> dict[str, dict]:
    """Les ReplicaSets de webapp, par image de leur template."""
    par_image: dict[str, dict] = {}
    for rs in _json(host, f"-n {NAMESPACE} get rs -l app={DEPLOYMENT}")["items"]:
        image = rs["spec"]["template"]["spec"]["containers"][0].get("image", "")
        par_image[image] = {
            "nom": rs["metadata"]["name"],
            "revision": int((rs["metadata"].get("annotations") or {}).get(REVISION, "0")),
            "voulus": rs["spec"].get("replicas", 0),
            "prets": rs["status"].get("readyReplicas", 0),
            "cause": (rs["metadata"].get("annotations") or {}).get(CAUSE, ""),
        }
    return par_image


# ----------------------------------------------------------------------
# 1. Le Deployment est sain, sur la bonne image.
# ----------------------------------------------------------------------
def test_le_deploiement_est_sain_sur_la_bonne_image(host):
    d: dict = {}
    for _ in range(18):
        d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}")
        if d["status"].get("availableReplicas", 0) == 3 and d["status"].get("updatedReplicas", 0) == 3:
            break
        time.sleep(5)
    image = d["spec"]["template"]["spec"]["containers"][0].get("image")
    assert image == IMAGE, (
        f"webapp demande l'image {image!r} au lieu de {IMAGE!r}. "
        + ("C'est encore l'image fautive : le déploiement bloqué n'a pas été défait." if image == IMAGE_FAUTIVE else "")
    )
    assert d["spec"].get("replicas") == 3, f"webapp demande {d['spec'].get('replicas')} replica(s) au lieu de 3."
    assert d["status"].get("availableReplicas", 0) == 3 and d["status"].get("updatedReplicas", 0) == 3, (
        f"{d['status'].get('availableReplicas', 0)} replica(s) disponible(s), "
        f"{d['status'].get('updatedReplicas', 0)} à jour, sur 3 : le déploiement n'est pas terminé."
    )
    en_erreur = [
        p["metadata"]["name"] for p in _json(host, f"-n {NAMESPACE} get pods -l app={DEPLOYMENT}")["items"]
        for s in p["status"].get("containerStatuses") or []
        if (s.get("state", {}).get("waiting") or {}).get("reason", "").startswith(("ImagePull", "ErrImage"))
    ]
    assert not en_erreur, f"Des Pods n'ont toujours pas d'image : {en_erreur}."


# ----------------------------------------------------------------------
# 2. Un retour arrière a eu lieu, par l'historique.
# ----------------------------------------------------------------------
def test_le_retour_arriere_a_ete_fait_par_l_historique(host):
    rs = _replicasets(host)
    assert IMAGE_AVANT in rs, (
        f"Aucun ReplicaSet de {IMAGE_AVANT} : l'historique de webapp a été perdu. Un Deployment "
        "recréé de zéro n'a plus de révision précédente vers laquelle revenir."
    )
    assert IMAGE_FAUTIVE in rs, f"Aucun ReplicaSet de {IMAGE_FAUTIVE} : l'historique a été effacé."
    assert rs[IMAGE_AVANT]["revision"] > rs[IMAGE_FAUTIVE]["revision"], (
        f"Le ReplicaSet de {IMAGE_AVANT} est resté à la révision {rs[IMAGE_AVANT]['revision']}, "
        f"celui de l'image fautive est à la {rs[IMAGE_FAUTIVE]['revision']}. Revenir en arrière "
        "réactive l'ancien ReplicaSet et lui donne un nouveau numéro : ce numéro n'a pas bougé, "
        "le déploiement bloqué n'a pas été défait avant de livrer la suite."
    )


# ----------------------------------------------------------------------
# 3. Le ReplicaSet fautif est encore là, à zéro.
# ----------------------------------------------------------------------
def test_la_version_fautive_est_conservee_a_zero(host):
    rs = _replicasets(host)
    assert IMAGE_FAUTIVE in rs, (
        f"Le ReplicaSet de {IMAGE_FAUTIVE} a disparu. L'historique d'un Deployment se garde : "
        "revenir en arrière le réduit à zéro, le supprimer à la main efface la trace."
    )
    assert rs[IMAGE_FAUTIVE]["voulus"] == 0, (
        f"Le ReplicaSet de {IMAGE_FAUTIVE} demande encore {rs[IMAGE_FAUTIVE]['voulus']} replica(s) : "
        "le déploiement bloqué est toujours en cours."
    )


# ----------------------------------------------------------------------
# 4. La révision finale porte sa cause.
# ----------------------------------------------------------------------
def test_la_revision_finale_porte_sa_cause(host):
    rs = _replicasets(host)
    assert IMAGE in rs and rs[IMAGE]["voulus"] == 3, f"Aucun ReplicaSet de {IMAGE} à trois replicas."
    assert rs[IMAGE]["revision"] == max(r["revision"] for r in rs.values()), (
        f"Le ReplicaSet de {IMAGE} n'est pas la dernière révision ({rs[IMAGE]['revision']})."
    )
    assert rs[IMAGE]["cause"].strip(), (
        f"La révision {rs[IMAGE]['revision']} n'a pas de cause de changement. L'annotation "
        f"{CAUSE} posée sur le Deployment est recopiée sur le ReplicaSet de la révision courante, "
        "et c'est elle que kubectl rollout history affiche dans CHANGE-CAUSE."
    )
