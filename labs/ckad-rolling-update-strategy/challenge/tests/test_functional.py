"""test_functional.py : ckad-rolling-update-strategy

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées, et jamais un
fichier YAML du poste.

Huit affirmations, une par état demandé par l'énoncé : la stratégie (son type,
son maxSurge, son maxUnavailable), l'image, les cinq replicas prêts sur la
NOUVELLE image, puis l'historique des ReplicaSets (deux révisions, la nouvelle
au complet, les anciennes à zéro).

CHAQUE TEST DOIT POUVOIR REFUSER AVANT LE TRAVAIL, et trois d'entre eux ne le
pouvaient pas, mesuré en campagne le 2026-11-10 : 3 tests sur 9 passaient sur
la situation de départ, donnant des points pour l'état initial.

  - La stratégie : RollingUpdate est le DÉFAUT de Kubernetes, un Deployment
    créé sans `spec.strategy` le porte déjà. C'est la SITUATION qui a changé,
    pas le test : `fixtures/prepare.sh` pose désormais `type: Recreate`, donc
    un état qui viole l'exigence.
  - Les cinq replicas prêts : ils l'étaient au départ, sur l'ancienne image, et
    `updatedReplicas` dit « conforme au template COURANT », pas « sur la
    nouvelle image ». Le test exige donc l'état final COMPLET, image du
    ReplicaSet courant comprise.
  - Les cinq replicas voulus : une exigence de NON-RÉGRESSION est vraie avant
    le travail par construction. Elle n'a plus de critère à elle, et vit comme
    assertion du test précédent, qui lui ne peut pas passer avant le travail.

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
IMAGE = "nginx:1.30.6"
IMAGE_AVANT = "nginx:1.30.5"
REPLICAS = 5
REVISION = "deployment.kubernetes.io/revision"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

#: Attente maximale d'un état transitoire : 18 essais de 5 s, soit 90 s.
ESSAIS = 18
PAUSE = 5


def _image(reference: str) -> str:
    """La référence d'image sans son digest.

    ``nginx:1.30.6@sha256:...`` et ``nginx:1.30.6`` désignent la même image, et
    la leçon jumelée épingle ses exemples par digest. Un apprenant qui copie ce
    style demande bien l'image attendue.
    """
    return reference.split("@", 1)[0]


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
    rattaches, orphelins = _replicasets_rattaches(host)
    # Tri par révision croissante : si deux ReplicaSets portent la même image,
    # c'est le plus récent que la table retient, pas celui que kubectl a listé
    # en dernier.
    par_image: dict[str, dict] = {
        rs["image"]: rs for rs in sorted(rattaches, key=lambda rs: rs["revision"])
    }
    return par_image, orphelins


def _replicasets_rattaches(host) -> tuple[list[dict], list[str]]:
    """Les ReplicaSets de webapp, un par objet, et les intrus non rattachés.

    La liste brute plutôt que la table par image : deux ReplicaSets peuvent
    porter la MÊME image et des révisions différentes, par exemple après un
    `kubectl rollout restart`, et l'un écraserait l'autre dans la table.
    """
    items = _json(host, f"-n {NAMESPACE} get replicasets -l app={DEPLOYMENT}", message(
        en="Cannot read the ReplicaSets.",
        fr="Lecture des ReplicaSets impossible.",
    ))["items"]
    rattaches: list[dict] = []
    orphelins: list[str] = []
    for rs in items:
        if not _appartient_au_deployment(rs):
            orphelins.append(rs["metadata"]["name"])
            continue
        rattaches.append({
            "nom": rs["metadata"]["name"],
            "image": _image(rs["spec"]["template"]["spec"]["containers"][0].get("image", "")),
            "revision": int((rs["metadata"].get("annotations") or {}).get(REVISION, "0")),
            "voulus": rs["spec"].get("replicas", 0),
            "actuels": rs["status"].get("replicas", 0),
            "prets": rs["status"].get("readyReplicas", 0),
        })
    return rattaches, orphelins


def _revision_courante(deploiement: dict) -> int:
    """Le numéro de révision que le Deployment déclare actif.

    Le contrôleur l'écrit sur le Deployment lui-même, et le ReplicaSet qui
    porte le même numéro est celui sur lequel tournent les Pods à jour.
    """
    return int((deploiement["metadata"].get("annotations") or {}).get(REVISION, "0"))


def _replicaset_de_revision(host, revision: int) -> dict:
    """Le ReplicaSet de cette révision, avec son image, ou {} s'il n'y en a pas.

    C'est par lui qu'on sait sur QUELLE image tournent les replicas prêts :
    `status.updatedReplicas` du Deployment ne le dit pas, il compte les Pods
    conformes au template courant, quel que soit ce template.
    """
    if not revision:
        return {}
    rattaches, _ = _replicasets_rattaches(host)
    for rs in rattaches:
        if rs["revision"] == revision:
            return rs
    return {}


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
    """Exige RollingUpdate, là où la situation pose Recreate.

    Ce test ne pourrait rien refuser si la situation partait de la stratégie
    par défaut, RollingUpdate étant ce défaut. C'est `fixtures/prepare.sh` qui
    rend l'exigence mesurable, en posant `type: Recreate` au départ.
    """
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
# 2. Le Deployment : son image, puis son état final complet.
# ----------------------------------------------------------------------
def test_l_image_est_la_nouvelle(host):
    image = _image(_deployment(host)["spec"]["template"]["spec"]["containers"][0].get("image", ""))
    assert image == IMAGE, message(
        en=f"The Deployment's image is {image!r}, expected {IMAGE!r}. The image of the Pod template "
        "is what a rolling update changes.",
        fr=f"L'image du Deployment est {image!r}, attendu {IMAGE!r}. C'est l'image du template de Pod "
        "qu'une mise à jour progressive change.",
    )


def test_les_cinq_replicas_sont_prets_sur_la_nouvelle_image(host):
    """Les cinq replicas sont prêts, à jour, ET sur la nouvelle image.

    POURQUOI L'ÉTAT FINAL COMPLET. Lire `readyReplicas == 5` et
    `updatedReplicas == 5` ne mesure rien ici : au départ, les cinq Pods de
    l'ancienne image sont prêts, et ils sont « à jour » au sens de Kubernetes,
    qui compare les Pods au template COURANT du Deployment sans savoir quelle
    image l'énoncé demande. Le test lit donc en plus l'image du ReplicaSet que
    le Deployment déclare actif : au départ elle vaut 1.30.5, et seul le travail
    l'amène sur 1.30.6. L'état mesuré reste un seul état, mais le travail est le
    seul chemin qui y mène.

    LA NON-RÉGRESSION DES CINQ REPLICAS EST ICI, et plus dans un test à elle.
    `test_les_replicas_restent_cinq` affirmait que `spec.replicas` vaut 5 : la
    situation les posant déjà, l'affirmation était vraie avant le travail, donc
    incapable de refuser. Aucune autre voie n'était acceptable, exiger un autre
    nombre au départ changeant le sujet. Elle est donc devenue une assertion de
    ce test, qui lui dépend du travail, et son critère séparé a disparu de
    `lab.yaml` et de `lab.fr.yaml`. On perd un critère, on gagne un contrôle
    qui mesure.
    """
    voulus = _deployment(host)["spec"].get("replicas")
    assert voulus == REPLICAS, message(
        en=f"The Deployment asks for {voulus} replica(s), expected {REPLICAS}. The exercise changes the "
        "strategy and the image; the size of the Deployment stays what the situation set.",
        fr=f"Le Deployment demande {voulus} replica(s), attendu {REPLICAS}. L'exercice change la "
        "stratégie et l'image ; la taille du Deployment reste celle que la situation a posée.",
    )

    statut: dict = {}
    courant: dict = {}
    for essai in range(ESSAIS):
        deploiement = _deployment(host)
        statut = deploiement["status"]
        courant = _replicaset_de_revision(host, _revision_courante(deploiement))
        if (
            statut.get("readyReplicas", 0) == REPLICAS
            and statut.get("updatedReplicas", 0) == REPLICAS
            and courant.get("image") == IMAGE
        ):
            break
        if essai < ESSAIS - 1:
            time.sleep(PAUSE)

    assert courant.get("image") == IMAGE, message(
        en=f"The replicas in service run {courant.get('image')!r}, expected {IMAGE!r}: the revision the "
        f"Deployment declares active is {courant.get('nom')!r} after {ESSAIS * PAUSE} s. Changing the "
        "image of the template is what triggers the replacement; until the switch has run, the Pods "
        "still carry the previous image. kubectl rollout status says where it stands.",
        fr=f"Les replicas en service portent {courant.get('image')!r}, attendu {IMAGE!r} : la révision "
        f"que le Deployment déclare active est {courant.get('nom')!r} après {ESSAIS * PAUSE} s. C'est le "
        "changement d'image du template qui déclenche le remplacement ; tant que la bascule n'a pas eu "
        "lieu, les Pods portent encore l'image précédente. kubectl rollout status dit où elle en est.",
    )
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
