"""test_functional.py : ckad-rolling-update-strategy

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées, et jamais un
fichier YAML du poste.

Neuf affirmations, une par état demandé par l'énoncé : la stratégie (son type,
son maxSurge, son maxUnavailable), l'image, le nombre de replicas voulus, les
replicas prêts et à jour, puis l'historique des ReplicaSets (deux révisions, la
nouvelle au complet, les anciennes à zéro).

CE QUE L'HISTORIQUE PROUVE, ET CE QU'IL NE PROUVE PAS. Les ReplicaSets
établissent qu'un remplacement progressif a eu lieu et qu'il est allé au bout ;
ce sont les trois premiers tests, et eux seuls, qui disent sous quelles
contraintes la stratégie est désormais posée. L'ordre des gestes (régler avant
de mettre à jour) n'est pas observable après coup : rien ici ne le mesure, et
l'énoncé le dit.

DEUX GARDE-FOUS CONTRE UN HISTORIQUE FABRIQUÉ. Un label ne fait pas une
filiation : tout ReplicaSet lu doit porter un `ownerReferences` vers le
Deployment `webapp`, sans quoi un ReplicaSet posé à la main, portant le bon
label et zéro replica, suffirait à simuler une ancienne révision. Et les
numéros de révision doivent croître : celui de la nouvelle image est
strictement supérieur à celui de l'ancienne, ce qu'un Deployment recréé puis
décoré d'un faux passé ne peut pas produire.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
DEPLOYMENT = "webapp"
IMAGE = "nginx:1.27-alpine"
IMAGE_AVANT = "nginx:1.26-alpine"
REPLICAS = 5
REVISION = "deployment.kubernetes.io/revision"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

#: Attente maximale d'un état transitoire : 18 essais de 5 s, soit 90 s.
ESSAIS = 18
PAUSE = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _deployment(host) -> dict:
    return _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", message(
        en=f"No Deployment {DEPLOYMENT} in {NAMESPACE}.",
        fr=f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.",
    ))


def _strategie(host) -> dict:
    return _deployment(host)["spec"].get("strategy") or {}


def _appartient_au_deployment(rs: dict) -> bool:
    """Le ReplicaSet est-il une révision de webapp, ou un objet posé à la main ?

    C'est le contrôle de filiation : le label `app=webapp` se pose sur
    n'importe quoi, l'`ownerReferences` est écrit par le contrôleur de
    Deployment et désigne le Deployment qui a engendré le ReplicaSet.
    """
    return any(
        ref.get("kind") == "Deployment" and ref.get("name") == DEPLOYMENT
        for ref in rs["metadata"].get("ownerReferences") or []
    )


def _lire_replicasets(host) -> tuple[dict[str, dict], list[str]]:
    """Les ReplicaSets de webapp par image, et les intrus non rattachés.

    Rend deux choses : la table des révisions réelles, indexée par l'image de
    leur template, et la liste des ReplicaSets qui portent le label du lab sans
    appartenir au Deployment. Les seconds ne sont pas ignorés en silence : un
    test les refuse explicitement.
    """
    items = _json(host, f"-n {NAMESPACE} get replicasets -l app={DEPLOYMENT}", message(
        en="Cannot read the ReplicaSets.",
        fr="Lecture des ReplicaSets impossible.",
    ))["items"]
    par_image: dict[str, dict] = {}
    orphelins: list[str] = []
    for rs in items:
        if not _appartient_au_deployment(rs):
            orphelins.append(rs["metadata"]["name"])
            continue
        image = rs["spec"]["template"]["spec"]["containers"][0].get("image", "")
        par_image[image] = {
            "nom": rs["metadata"]["name"],
            "revision": int((rs["metadata"].get("annotations") or {}).get(REVISION, "0")),
            "voulus": rs["spec"].get("replicas", 0),
            "actuels": rs["status"].get("replicas", 0),
            "prets": rs["status"].get("readyReplicas", 0),
        }
    return par_image, orphelins


def _attendre_replicasets(host, stable) -> tuple[dict[str, dict], list[str]]:
    """Relit les ReplicaSets jusqu'à ce que `stable` soit vrai, ou 90 s.

    Une mise à jour progressive à `maxSurge: 2` autorise un chevauchement :
    l'ancien ReplicaSet peut encore porter des Pods pendant que le nouveau
    monte, et le lire une seule fois ferait rougir un travail correct, juste
    fini. Les deux tests qui lisent un compte de replicas attendent donc, comme
    celui qui lit le Deployment.
    """
    par_image: dict[str, dict] = {}
    orphelins: list[str] = []
    for essai in range(ESSAIS):
        par_image, orphelins = _lire_replicasets(host)
        if stable(par_image):
            break
        if essai < ESSAIS - 1:
            time.sleep(PAUSE)
    return par_image, orphelins


# ----------------------------------------------------------------------
# 1. La stratégie : son type, puis ses deux bornes.
# ----------------------------------------------------------------------
def test_la_strategie_est_rollingupdate(host):
    strategie = _strategie(host)
    assert strategie.get("type") == "RollingUpdate", message(
        en=f"The strategy of {DEPLOYMENT} is {strategie.get('type')!r}, expected 'RollingUpdate'. "
        "Recreate kills every Pod before starting the new ones, which the service does not tolerate. "
        "The strategy lives under spec.strategy of the Deployment.",
        fr=f"La stratégie de {DEPLOYMENT} est {strategie.get('type')!r}, attendu 'RollingUpdate'. "
        "Recreate tue tous les Pods avant de démarrer les nouveaux, ce que le service ne tolère pas. "
        "La stratégie vit sous spec.strategy du Deployment.",
    )


def test_maxsurge_vaut_deux(host):
    ru = _strategie(host).get("rollingUpdate") or {}
    assert str(ru.get("maxSurge")) == "2", message(
        en=f"maxSurge is {ru.get('maxSurge')!r}, expected 2: at most two extra Pods during the switch. "
        "The default, 25 %, would also allow two out of five, but a percentage is not the asked value: "
        "it would follow the replica count, and the cluster's spare room does not.",
        fr=f"maxSurge vaut {ru.get('maxSurge')!r}, attendu 2 : au plus deux Pods en trop pendant la bascule. "
        "La valeur par défaut, 25 %, en autoriserait deux sur cinq aussi, mais un pourcentage n'est pas "
        "la valeur demandée : il suivrait le nombre de replicas, ce que la place libre du cluster ne fait pas.",
    )


def test_maxunavailable_vaut_un(host):
    ru = _strategie(host).get("rollingUpdate") or {}
    assert str(ru.get("maxUnavailable")) == "1", message(
        en=f"maxUnavailable is {ru.get('maxUnavailable')!r}, expected 1: at most one Pod unavailable "
        "at a time. It sits beside maxSurge, under spec.strategy.rollingUpdate.",
        fr=f"maxUnavailable vaut {ru.get('maxUnavailable')!r}, attendu 1 : au plus un Pod indisponible "
        "à la fois. Il se pose à côté de maxSurge, sous spec.strategy.rollingUpdate.",
    )


# ----------------------------------------------------------------------
# 2. Le Deployment : son image, sa taille, son état.
# ----------------------------------------------------------------------
def test_l_image_est_la_nouvelle(host):
    image = _deployment(host)["spec"]["template"]["spec"]["containers"][0].get("image")
    assert image == IMAGE, message(
        en=f"The Deployment's image is {image!r}, expected {IMAGE!r}. The image of the Pod template "
        "is what a rolling update changes.",
        fr=f"L'image du Deployment est {image!r}, attendu {IMAGE!r}. C'est l'image du template de Pod "
        "qu'une mise à jour progressive change.",
    )


def test_les_replicas_restent_cinq(host):
    voulus = _deployment(host)["spec"].get("replicas")
    assert voulus == REPLICAS, message(
        en=f"The Deployment asks for {voulus} replica(s), expected {REPLICAS}. The exercise changes the "
        "strategy and the image; the size of the Deployment stays what the situation set.",
        fr=f"Le Deployment demande {voulus} replica(s), attendu {REPLICAS}. L'exercice change la "
        "stratégie et l'image ; la taille du Deployment reste celle que la situation a posée.",
    )


def test_les_cinq_replicas_sont_prets_et_a_jour(host):
    statut: dict = {}
    for essai in range(ESSAIS):
        statut = _deployment(host)["status"]
        if statut.get("readyReplicas", 0) == REPLICAS and statut.get("updatedReplicas", 0) == REPLICAS:
            break
        if essai < ESSAIS - 1:
            time.sleep(PAUSE)
    assert statut.get("readyReplicas", 0) == REPLICAS and statut.get("updatedReplicas", 0) == REPLICAS, message(
        en=f"{statut.get('readyReplicas', 0)} ready, {statut.get('updatedReplicas', 0)} up to date "
        f"out of {REPLICAS} after {ESSAIS * PAUSE} s: the update did not go all the way through. "
        "kubectl rollout status says where it stands, and the Pods' events say why.",
        fr=f"{statut.get('readyReplicas', 0)} prêts, {statut.get('updatedReplicas', 0)} à jour "
        f"sur {REPLICAS} après {ESSAIS * PAUSE} s : la mise à jour n'est pas allée au bout. "
        "kubectl rollout status dit où elle en est, et les events des Pods disent pourquoi.",
    )


# ----------------------------------------------------------------------
# 3. L'historique : deux révisions, la nouvelle au complet, l'ancienne à zéro.
# ----------------------------------------------------------------------
def test_deux_revisions_existent(host):
    par_image, orphelins = _lire_replicasets(host)
    assert not orphelins, message(
        en=f"{orphelins} carry the label app={DEPLOYMENT} without belonging to the Deployment "
        f"{DEPLOYMENT}: no ownerReferences names it. A ReplicaSet created by hand is not a revision "
        "of webapp, and the history of an update is not something one writes afterwards. "
        "Remove them and let the Deployment produce its own.",
        fr=f"{orphelins} portent le label app={DEPLOYMENT} sans appartenir au Deployment "
        f"{DEPLOYMENT} : aucun ownerReferences ne le nomme. Un ReplicaSet créé à la main n'est pas une "
        "révision de webapp, et l'historique d'une mise à jour ne s'écrit pas après coup. "
        "Retirez-les et laissez le Deployment produire les siens.",
    )
    assert len(par_image) >= 2, message(
        en=f"{len(par_image)} ReplicaSet owned by {DEPLOYMENT}: a rolling update creates a new one and "
        "keeps the previous one at zero. A single ReplicaSet means the Deployment was recreated rather "
        "than updated, and a recreated Deployment has no history.",
        fr=f"{len(par_image)} ReplicaSet appartenant à {DEPLOYMENT} : une mise à jour progressive en crée "
        "un nouveau et garde le précédent à zéro. Un seul ReplicaSet signifie que le Deployment a été "
        "recréé plutôt que mis à jour, et un Deployment recréé n'a pas d'historique.",
    )
    assert IMAGE in par_image, message(
        en=f"No ReplicaSet owned by {DEPLOYMENT} runs {IMAGE}. Images present: {sorted(par_image)}",
        fr=f"Aucun ReplicaSet appartenant à {DEPLOYMENT} ne porte {IMAGE}. Images présentes : {sorted(par_image)}",
    )
    assert IMAGE_AVANT in par_image, message(
        en=f"No ReplicaSet owned by {DEPLOYMENT} runs {IMAGE_AVANT}: the revision the situation started "
        "from has been lost. Deleting it by hand, or recreating the Deployment, erases the trace that "
        "makes a rollback possible.",
        fr=f"Aucun ReplicaSet appartenant à {DEPLOYMENT} ne porte {IMAGE_AVANT} : la révision dont partait "
        "la situation a été perdue. La supprimer à la main, ou recréer le Deployment, efface la trace qui "
        "rend un retour arrière possible.",
    )
    nouvelle = par_image[IMAGE]["revision"]
    ancienne = par_image[IMAGE_AVANT]["revision"]
    assert nouvelle > ancienne, message(
        en=f"The ReplicaSet for {IMAGE} is revision {nouvelle}, the one for {IMAGE_AVANT} is revision "
        f"{ancienne}. The new image must come AFTER the old one in the Deployment's history: each "
        f"rollout gives the ReplicaSet it activates a higher {REVISION} number. These numbers do not "
        "tell that story, so the new image is not the result of an update of this Deployment.",
        fr=f"Le ReplicaSet de {IMAGE} est à la révision {nouvelle}, celui de {IMAGE_AVANT} à la révision "
        f"{ancienne}. La nouvelle image doit venir APRÈS l'ancienne dans l'historique du Deployment : "
        f"chaque déploiement donne au ReplicaSet qu'il active un numéro {REVISION} plus élevé. Ces "
        "numéros ne racontent pas cela, la nouvelle image n'est donc pas le résultat d'une mise à jour "
        "de ce Deployment.",
    )


def test_le_nouveau_replicaset_porte_cinq_replicas(host):
    par_image, _ = _attendre_replicasets(
        host,
        lambda rs: (rs.get(IMAGE) or {}).get("prets") == REPLICAS,
    )
    nouveau = par_image.get(IMAGE)
    assert nouveau, message(
        en=f"No ReplicaSet owned by {DEPLOYMENT} runs {IMAGE}. Images present: {sorted(par_image)}",
        fr=f"Aucun ReplicaSet appartenant à {DEPLOYMENT} ne porte {IMAGE}. Images présentes : {sorted(par_image)}",
    )
    assert nouveau["voulus"] == REPLICAS and nouveau["prets"] == REPLICAS, message(
        en=f"The ReplicaSet {nouveau['nom']} for {IMAGE} asks for {nouveau['voulus']} replica(s) and has "
        f"{nouveau['prets']} ready, expected {REPLICAS} and {REPLICAS} after {ESSAIS * PAUSE} s. "
        "The new revision is not complete: kubectl describe rs says what holds its Pods back.",
        fr=f"Le ReplicaSet {nouveau['nom']} de {IMAGE} demande {nouveau['voulus']} replica(s) et en a "
        f"{nouveau['prets']} prêt(s), attendu {REPLICAS} et {REPLICAS} après {ESSAIS * PAUSE} s. "
        "La nouvelle révision n'est pas au complet : kubectl describe rs dit ce qui retient ses Pods.",
    )


def test_les_anciens_replicasets_sont_a_zero(host):
    def retombes(rs: dict[str, dict]) -> bool:
        anciens = [r for img, r in rs.items() if img != IMAGE]
        return bool(anciens) and all(r["voulus"] == 0 and r["actuels"] == 0 for r in anciens)

    par_image, _ = _attendre_replicasets(host, retombes)
    anciens = {img: r for img, r in par_image.items() if img != IMAGE}
    assert anciens, message(
        en=f"No ReplicaSet other than {IMAGE}'s is owned by {DEPLOYMENT}: there is nothing left of the "
        "previous revision, so nothing shows a replacement took place.",
        fr=f"Aucun ReplicaSet autre que celui de {IMAGE} n'appartient à {DEPLOYMENT} : il ne reste rien de "
        "la révision précédente, donc rien ne montre qu'un remplacement a eu lieu.",
    )
    restants = {
        img: {"voulus": r["voulus"], "actuels": r["actuels"]}
        for img, r in anciens.items()
        if r["voulus"] != 0 or r["actuels"] != 0
    }
    assert not restants, message(
        en=f"The old ReplicaSets still carry Pods after {ESSAIS * PAUSE} s: {restants}. A finished "
        "rolling update leaves them at zero, kept as history. kubectl rollout status tells whether "
        "the switch is still running or stuck.",
        fr=f"Les anciens ReplicaSets portent encore des Pods après {ESSAIS * PAUSE} s : {restants}. Une "
        "mise à jour progressive terminée les laisse à zéro, conservés comme historique. "
        "kubectl rollout status dit si la bascule est encore en cours ou bloquée.",
    )
