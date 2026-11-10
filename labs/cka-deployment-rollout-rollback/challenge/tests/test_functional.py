"""test_functional.py : cka-deployment-rollout-rollback

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées, et jamais un
fichier YAML du poste.

Un test vérifie un seul état demandé par l'énoncé. Les quatre premiers lisent
le Deployment lui-même : l'image qu'il demande, le nombre de replicas qu'il
demande, les replicas réellement disponibles et à jour, et l'absence de Pod
resté sans image. Les quatre suivants lisent les ReplicaSets du Deployment et
leurs numéros de révision : l'historique conservé, la révision de la version
d'avant, la version fautive gardée à zéro, et la révision finale. Le dernier
lit la cause de changement LÀ OÙ L'ÉNONCÉ LA DEMANDE, sur le Deployment.

Deux choix de mesure, qui valent d'être dits.

1. Les ReplicaSets sont sélectionnés par leur PROPRIÉTAIRE
   (``ownerReferences`` qui nomme le Deployment webapp), pas par le label
   ``app=webapp``. Un second Deployment qui porterait le même label
   injecterait sinon ses propres ReplicaSets dans la mesure. Les Pods sont
   filtrés de la même façon, par le ReplicaSet qui les possède.

2. Les numéros de révision sont comparés à leurs VALEURS attendues, pas entre
   eux. Un simple ordre se reproduit à la main, et ces annotations sont
   écrivables : exiger les valeurs exactes ne rend pas la triche impossible,
   mais elle ne coûte plus moins cher que le travail demandé.

Ce que ces tests NE prouvent PAS, et qu'ils ne prétendent donc pas prouver :
le geste. Un retour à l'image précédente par ``kubectl set image`` laisse
exactement le même état qu'un ``kubectl rollout undo`` : même ReplicaSet
réutilisé, même nouveau numéro de révision. L'énoncé recommande ``rollout
undo``, qui est le geste de l'examen, et les messages d'échec parlent de
l'état manquant, jamais d'un geste qui n'aurait pas été fait.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
DEPLOYMENT = "webapp"
CONTENEUR = "nginx"
IMAGE_AVANT = "nginx:1.26-alpine"
IMAGE_FAUTIVE = "nginx:1.27-alpin"
IMAGE = "nginx:1.27-alpine"
REPLICAS = 3

#: Les révisions attendues à la fin, telles que l'énoncé les demande.
#: 1 = l'application d'origine, 2 = la mise à jour fautive de ce matin,
#: 3 = la version d'avant remise en service, 4 = la bonne image livrée.
REV_FAUTIVE = 2
REV_AVANT = 3
REV_FINALE = 4

REVISION = "deployment.kubernetes.io/revision"
CAUSE = "kubernetes.io/change-cause"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

#: L'attente, une seule fois dans tout le fichier : le temps que le rollout
#: de la bonne image finisse. 2 secondes de pas, 60 secondes au plus, et on
#: sort dès que l'état est atteint.
PAS = 2
ESSAIS = 30


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str) -> dict:
    res = _kubectl(host, args + " -o json")
    assert res.rc == 0, message(
        en=f"kubectl {args} failed: {res.stderr.strip()[:200]}",
        fr=f"kubectl {args} échoue : {res.stderr.strip()[:200]}",
    )
    return json.loads(res.stdout)


def _image(reference: str) -> str:
    """La référence d'image sans son digest.

    ``nginx:1.27-alpine@sha256:...`` et ``nginx:1.27-alpine`` désignent la
    même image, et la leçon jumelée épingle son exemple par digest. Un
    apprenant qui copie ce style demande bien l'image attendue.
    """
    return reference.split("@", 1)[0]


def _deploiement(host) -> dict:
    return _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}")


def _image_demandee(deploiement: dict) -> str:
    conteneurs = deploiement["spec"]["template"]["spec"]["containers"]
    return _image(conteneurs[0].get("image", ""))


def _possede_par_le_deploiement(objet: dict, noms: set[str], kind: str) -> bool:
    return any(
        ref.get("kind") == kind and ref.get("name") in noms
        for ref in objet["metadata"].get("ownerReferences") or []
    )


def _replicasets_bruts(host) -> list[dict]:
    """Les ReplicaSets dont le propriétaire est LE Deployment webapp.

    Le label ne suffit pas : il se pose sur n'importe quel objet, donc un
    Deployment voisin qui porterait ``app: webapp`` fournirait des
    ReplicaSets à la mesure. La propriété, elle, est posée par le
    contrôleur.
    """
    return [
        rs for rs in _json(host, f"-n {NAMESPACE} get rs")["items"]
        if _possede_par_le_deploiement(rs, {DEPLOYMENT}, "Deployment")
    ]


def _replicasets(host) -> dict[str, dict]:
    """Les ReplicaSets de webapp, par image de leur template."""
    par_image: dict[str, dict] = {}
    for rs in _replicasets_bruts(host):
        image = _image(rs["spec"]["template"]["spec"]["containers"][0].get("image", ""))
        annotations = rs["metadata"].get("annotations") or {}
        par_image[image] = {
            "nom": rs["metadata"]["name"],
            "revision": int(annotations.get(REVISION, "0")),
            "voulus": rs["spec"].get("replicas", 0),
            "prets": rs["status"].get("readyReplicas", 0),
            "cause": annotations.get(CAUSE, ""),
        }
    return par_image


def _pods(host) -> list[dict]:
    """Les Pods possédés par les ReplicaSets de webapp, et eux seuls."""
    noms = {rs["metadata"]["name"] for rs in _replicasets_bruts(host)}
    if not noms:
        return []
    return [
        pod for pod in _json(host, f"-n {NAMESPACE} get pods")["items"]
        if _possede_par_le_deploiement(pod, noms, "ReplicaSet")
    ]


def _absent(image: str, role_en: str, role_fr: str) -> str:
    return message(
        en=f"No ReplicaSet of webapp carries the image {image!r} ({role_en}). "
        "kubectl get rs -n lab shows the ReplicaSets that remain, and "
        "kubectl rollout history deployment/webapp -n lab their revisions.",
        fr=f"Aucun ReplicaSet de webapp ne porte l'image {image!r} ({role_fr}). "
        "kubectl get rs -n lab montre les ReplicaSets qui restent, et "
        "kubectl rollout history deployment/webapp -n lab leurs révisions.",
    )


@pytest.fixture(scope="module")
def deploiement_stabilise(host) -> dict:
    """Le Deployment une fois son rollout terminé, ou le dernier état vu.

    C'est la SEULE attente du fichier. Elle sort dès que les trois replicas
    sont disponibles et à jour, et elle renonce tout de suite si le
    Deployment ne demande pas encore l'état visé : attendre ne fera pas
    arriver trois replicas d'une image qui n'est pas celle qu'on attend, et
    c'est un autre test qui juge ce qu'il demande.
    """
    d = _deploiement(host)
    for essai in range(ESSAIS):
        statut = d["status"]
        if (
            statut.get("availableReplicas", 0) == REPLICAS
            and statut.get("updatedReplicas", 0) == REPLICAS
        ):
            break
        if _image_demandee(d) != IMAGE or d["spec"].get("replicas") != REPLICAS:
            break
        if essai < ESSAIS - 1:
            time.sleep(PAS)
            d = _deploiement(host)
    return d


# ----------------------------------------------------------------------
# 1. Ce que le Deployment demande.
# ----------------------------------------------------------------------
def test_le_deploiement_demande_la_bonne_image(host):
    image = _image_demandee(_deploiement(host))
    detail_en = (
        " This is still the faulty image of this morning: the Deployment "
        "has not left that revision." if image == IMAGE_FAUTIVE else ""
    )
    detail_fr = (
        " C'est encore l'image fautive de ce matin : le Deployment n'a pas "
        "quitté cette révision." if image == IMAGE_FAUTIVE else ""
    )
    assert image == IMAGE, message(
        en=f"webapp asks for image {image!r} instead of {IMAGE!r}.{detail_en} "
        f"The container of the template is named {CONTENEUR!r}; a digest "
        "appended to the expected tag is accepted.",
        fr=f"webapp demande l'image {image!r} au lieu de {IMAGE!r}.{detail_fr} "
        f"Le conteneur du template s'appelle {CONTENEUR!r} ; un digest "
        "ajouté au tag attendu est accepté.",
    )


def test_le_deploiement_demande_trois_replicas(host):
    voulus = _deploiement(host)["spec"].get("replicas")
    assert voulus == REPLICAS, message(
        en=f"webapp asks for {voulus} replica(s) instead of {REPLICAS}. "
        "The number of replicas is not changed by an image update: it is the "
        "one the Deployment carried before, and it must stay.",
        fr=f"webapp demande {voulus} replica(s) au lieu de {REPLICAS}. "
        "Le nombre de replicas ne change pas lors d'une mise à jour d'image : "
        "c'est celui que le Deployment portait avant, et il doit le rester.",
    )


def test_les_trois_replicas_sont_disponibles_et_a_jour(deploiement_stabilise):
    statut = deploiement_stabilise["status"]
    disponibles = statut.get("availableReplicas", 0)
    a_jour = statut.get("updatedReplicas", 0)
    assert disponibles == REPLICAS and a_jour == REPLICAS, message(
        en=f"{disponibles} replica(s) available and {a_jour} up to date, out of "
        f"{REPLICAS}: the rollout is not finished. kubectl rollout status "
        "deployment/webapp -n lab waits for it, and kubectl describe "
        "deployment webapp -n lab says what blocks it.",
        fr=f"{disponibles} replica(s) disponible(s) et {a_jour} à jour, sur "
        f"{REPLICAS} : le déploiement n'est pas terminé. kubectl rollout status "
        "deployment/webapp -n lab l'attend, et kubectl describe deployment "
        "webapp -n lab dit ce qui le bloque.",
    )


def test_aucun_pod_n_est_en_erreur_d_image(host):
    en_erreur = [
        pod["metadata"]["name"] for pod in _pods(host)
        for etat in pod["status"].get("containerStatuses") or []
        if (etat.get("state", {}).get("waiting") or {})
        .get("reason", "")
        .startswith(("ImagePull", "ErrImage", "InvalidImageName"))
    ]
    assert not en_erreur, message(
        en=f"These Pods of webapp still have no image: {en_erreur}. A Pod that "
        "cannot pull its image belongs to a revision that asks for an image "
        "that does not exist; kubectl describe pod names it.",
        fr=f"Ces Pods de webapp n'ont toujours pas d'image : {en_erreur}. Un Pod "
        "qui n'arrive pas à tirer son image appartient à une révision qui "
        "demande une image inexistante ; kubectl describe pod la nomme.",
    )


# ----------------------------------------------------------------------
# 2. Ce que l'historique raconte.
# ----------------------------------------------------------------------
def test_l_historique_du_deploiement_est_intact(host):
    rs = _replicasets(host)
    assert IMAGE_AVANT in rs, message(
        en=f"No ReplicaSet of webapp carries {IMAGE_AVANT!r}, the version that "
        "worked. A Deployment deleted and recreated starts a new history, "
        "and that history no longer holds a previous revision.",
        fr=f"Aucun ReplicaSet de webapp ne porte {IMAGE_AVANT!r}, la version qui "
        "marchait. Un Deployment supprimé puis recréé repart sur un nouvel "
        "historique, et cet historique ne porte plus de révision précédente.",
    )
    assert IMAGE_FAUTIVE in rs, message(
        en=f"No ReplicaSet of webapp carries {IMAGE_FAUTIVE!r}, the faulty "
        "update. A history is kept: a revision is scaled down, never deleted.",
        fr=f"Aucun ReplicaSet de webapp ne porte {IMAGE_FAUTIVE!r}, la mise à "
        "jour fautive. Un historique se garde : une révision se réduit, elle "
        "ne se supprime pas.",
    )


def test_le_retour_arriere_a_ete_fait_avant_la_livraison(host):
    rs = _replicasets(host)
    avant = rs.get(IMAGE_AVANT)
    assert avant is not None, _absent(IMAGE_AVANT, "the version that worked", "la version qui marchait")
    fautive = rs.get(IMAGE_FAUTIVE)
    assert fautive is not None, _absent(IMAGE_FAUTIVE, "the faulty update", "la mise à jour fautive")
    assert fautive["revision"] == REV_FAUTIVE, message(
        en=f"The faulty update should be revision {REV_FAUTIVE} of webapp, it is "
        f"revision {fautive['revision']}. That revision is the one of this "
        "morning: it is not meant to move again.",
        fr=f"La mise à jour fautive doit être la révision {REV_FAUTIVE} de webapp, "
        f"elle est la révision {fautive['revision']}. Cette révision est celle "
        "de ce matin : elle n'a pas à bouger de nouveau.",
    )
    assert avant["revision"] == REV_AVANT, message(
        en=f"The version that worked is at revision {avant['revision']} of webapp, "
        f"expected {REV_AVANT}: it was not put back in service between the "
        "faulty update and the final delivery. Going back to the previous "
        "revision reuses its ReplicaSet and gives it a new number.",
        fr=f"La version qui marchait est à la révision {avant['revision']} de "
        f"webapp, attendu {REV_AVANT} : elle n'a pas été remise en service "
        "entre la mise à jour fautive et la livraison finale. Revenir à la "
        "révision précédente réutilise son ReplicaSet et lui donne un "
        "nouveau numéro.",
    )


def test_la_version_fautive_est_conservee_a_zero(host):
    fautive = _replicasets(host).get(IMAGE_FAUTIVE)
    assert fautive is not None, _absent(IMAGE_FAUTIVE, "the faulty update", "la mise à jour fautive")
    assert fautive["voulus"] == 0, message(
        en=f"The ReplicaSet {fautive['nom']} of {IMAGE_FAUTIVE!r} still asks for "
        f"{fautive['voulus']} replica(s): the faulty revision is still in "
        "service. Leaving a revision means scaling its ReplicaSet to zero, "
        "which the Deployment does by itself.",
        fr=f"Le ReplicaSet {fautive['nom']} de {IMAGE_FAUTIVE!r} demande encore "
        f"{fautive['voulus']} replica(s) : la révision fautive est toujours en "
        "service. Quitter une révision réduit son ReplicaSet à zéro, ce que "
        "le Deployment fait de lui-même.",
    )


def test_la_revision_finale_est_celle_de_la_bonne_image(host):
    finale = _replicasets(host).get(IMAGE)
    assert finale is not None, _absent(IMAGE, "the image to ship", "l'image à livrer")
    assert finale["revision"] == REV_FINALE, message(
        en=f"The ReplicaSet of {IMAGE!r} is revision {finale['revision']} of webapp, "
        f"expected {REV_FINALE}: the right image was not shipped last. Four "
        "revisions are expected in the end, and this one closes them.",
        fr=f"Le ReplicaSet de {IMAGE!r} est la révision {finale['revision']} de "
        f"webapp, attendu {REV_FINALE} : la bonne image n'a pas été livrée en "
        "dernier. Quatre révisions sont attendues à la fin, et celle-ci les "
        "ferme.",
    )
    assert finale["voulus"] == REPLICAS, message(
        en=f"The ReplicaSet {finale['nom']} of {IMAGE!r} asks for "
        f"{finale['voulus']} replica(s) instead of {REPLICAS}: the revision of "
        "the right image is not the one serving the traffic.",
        fr=f"Le ReplicaSet {finale['nom']} de {IMAGE!r} demande "
        f"{finale['voulus']} replica(s) au lieu de {REPLICAS} : la révision de "
        "la bonne image n'est pas celle qui sert le trafic.",
    )


# ----------------------------------------------------------------------
# 3. La cause de changement, là où l'énoncé la demande.
# ----------------------------------------------------------------------
def test_le_deploiement_porte_la_cause_de_changement(host):
    annotations = _deploiement(host)["metadata"].get("annotations") or {}
    cause = annotations.get(CAUSE, "")
    assert cause.strip(), message(
        en=f"The Deployment webapp carries no {CAUSE} annotation, or it is empty. "
        "The annotation is read on the Deployment, which is where it is asked "
        "for; kubectl annotate sets it, and kubectl rollout history shows it "
        "under CHANGE-CAUSE.",
        fr=f"Le Deployment webapp ne porte pas d'annotation {CAUSE}, ou elle est "
        "vide. L'annotation est lue sur le Deployment, là où elle est "
        "demandée ; kubectl annotate la pose, et kubectl rollout history "
        "l'affiche dans la colonne CHANGE-CAUSE.",
    )
