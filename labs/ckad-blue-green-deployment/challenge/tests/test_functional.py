"""test_functional.py : ckad-blue-green-deployment

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées ni un fichier
YAML du poste.

Dix affirmations, une par état demandé par l'énoncé. Le découpage n'est pas
cosmétique : la version précédente portait six assertions dans un seul test, et
le premier échec cachait les cinq autres. L'apprenant lisait « app-blue demande
1 replica » et n'apprenait rien des labels, des endpoints ni des requêtes.

Les deux tests qui comptent le plus sont `test_blue_sert_sa_version` et
`test_green_sert_sa_version` : ils interrogent CHAQUE Pod sur son adresse, sans
passer par le Service. Sans celui de blue, un `sleep 3600` sans serveur suffisait
à rendre 100, alors que tout le blue-green repose sur le fait que l'ancienne
version reste debout ET servante : c'est elle qui rend le retour arrière
instantané. Un lab qui ne le mesure pas se réduit à étiqueter un Deployment.

Le Pod `client` est l'instrument de mesure, et il vit dans le namespace que
l'apprenant contrôle. Deux précautions, parce qu'un instrument qu'on peut
remplacer ne mesure plus rien : la fixture `client` vérifie que c'est bien
l'image posée par le setup, et chaque requête passe par `/bin/busybox wget`,
donc par le binaire de l'image, et non par le premier `wget` du PATH.

Les adresses des Pods sont relues à CHAQUE tour d'attente. Les capturer une
fois avant la boucle faisait échouer le test en désignant un faux coupable dès
qu'un Pod était recréé pendant la minute d'observation.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
SERVICE = "app-prod"
CLIENT = "client"
CLIENT_IMAGE = "busybox:1.37"
APPLICATION = "myapp"
PORT = 8080
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

#: Durée d'observation et pas entre deux tours. Chaque test qui dépend d'une
#: convergence (replicas disponibles, endpoints, réponses du Service) porte sa
#: propre attente : un test ne doit jamais tenir parce qu'un autre, joué avant,
#: a attendu pour lui. Joué seul, il rendait sinon un faux rouge.
ATTENTE = 60
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def client(host):
    """L'instrument de mesure, vérifié avant de s'en servir.

    Le Pod `client` est posé par le setup dans le namespace de travail. Rien
    n'empêche de le remplacer par un conteneur dont le `wget` affiche `green`
    quoi qu'on lui demande : le lab rendrait alors 100 sans qu'une seule requête
    ait atteint l'application. On contrôle donc son identité, et les requêtes
    passent par `/bin/busybox`, le binaire de l'image, pas par le PATH.
    """
    pod = _json(host, f"-n {NAMESPACE} get pod {CLIENT}", message(
        en=f"No Pod {CLIENT} in {NAMESPACE}. The lab setup posed it: bring the "
        "starting situation back with 'dsoxlab reset ckad-blue-green-deployment'.",
        fr=f"Aucun Pod {CLIENT} dans {NAMESPACE}. Le setup du lab l'a posé : "
        "ramène la situation de départ avec "
        "'dsoxlab reset ckad-blue-green-deployment'.",
    ))
    assert pod["status"].get("phase") == "Running", message(
        en=f"The Pod {CLIENT} is in phase {pod['status'].get('phase')!r}: the lab "
        "has no way left to make a request. Bring it back with "
        "'dsoxlab reset ckad-blue-green-deployment'.",
        fr=f"Le Pod {CLIENT} est en phase {pod['status'].get('phase')!r} : le lab "
        "n'a plus de moyen de faire une requête. Ramène-le avec "
        "'dsoxlab reset ckad-blue-green-deployment'.",
    )
    images = [c.get("image") for c in pod["spec"].get("containers") or []]
    assert images == [CLIENT_IMAGE], message(
        en=f"The Pod {CLIENT} runs {images}, whereas the setup posed a single "
        f"{CLIENT_IMAGE} container. It is the measuring instrument of this lab, "
        "not part of what you have to build: replaced, it no longer measures the "
        "application. Bring it back with "
        "'dsoxlab reset ckad-blue-green-deployment'.",
        fr=f"Le Pod {CLIENT} tourne avec {images}, alors que le setup a posé un "
        f"seul conteneur {CLIENT_IMAGE}. C'est l'instrument de mesure du lab, pas "
        "une partie de ce qui est à construire : remplacé, il ne mesure plus "
        "l'application. Ramène-le avec "
        "'dsoxlab reset ckad-blue-green-deployment'.",
    )
    return pod


# ----------------------------------------------------------------------
# Lecture du cluster.
# ----------------------------------------------------------------------
def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _deployment(host, couleur: str) -> dict | None:
    """Le Deployment d'une couleur, ou None s'il n'existe pas.

    Pas d'assertion ici : c'est le test appelant qui dit l'absence, avec son
    propre message. Un helper qui lève prive le test de sa consigne.
    """
    res = _kubectl(host, f"-n {NAMESPACE} get deployment app-{couleur} -o json")
    if res.rc != 0:
        return None
    return json.loads(res.stdout)


def _pods(host, couleur: str) -> list[dict]:
    """Les Pods qui portent les labels attendus pour cette couleur."""
    res = _kubectl(
        host,
        f"-n {NAMESPACE} get pods -l app={APPLICATION},version={couleur} -o json",
    )
    if res.rc != 0:
        return []
    return json.loads(res.stdout).get("items") or []


def _pods_prets(host, couleur: str) -> list[dict]:
    """Les Pods de cette couleur qui tournent et sont prêts, avec une adresse."""
    prets = []
    for pod in _pods(host, couleur):
        if pod["status"].get("phase") != "Running" or not pod["status"].get("podIP"):
            continue
        conditions = {
            c.get("type"): c.get("status") for c in pod["status"].get("conditions") or []
        }
        if conditions.get("Ready") == "True":
            prets.append(pod)
    return prets


def _adresses(host, couleur: str) -> set[str]:
    return {p["status"]["podIP"] for p in _pods_prets(host, couleur)}


def _endpoints(host) -> set[str]:
    """Les adresses prêtes que le Service vise réellement, à cet instant."""
    res = _kubectl(
        host,
        f"-n {NAMESPACE} get endpointslices "
        f"-l kubernetes.io/service-name={SERVICE} -o json",
    )
    if res.rc != 0:
        return set()
    tranches = json.loads(res.stdout).get("items") or []
    return {
        adresse
        for tranche in tranches
        for point in tranche.get("endpoints") or []
        for adresse in point.get("addresses") or []
        if (point.get("conditions") or {}).get("ready")
    }


def _requete(host, cible: str):
    """Une requête HTTP depuis le client, par le binaire busybox de l'image.

    `/bin/busybox wget` et non `wget` : un `wget` déposé dans le PATH du
    conteneur afficherait ce qu'on veut, et le lab mesurerait ce faux.
    """
    return _kubectl(
        host,
        f"-n {NAMESPACE} exec {CLIENT} -- /bin/busybox wget -qO- -T 5 {cible}",
    )


def _reponses_des_pods(host, couleur: str) -> dict[str, str]:
    """Ce que répond chaque Pod de cette couleur, interrogé sur son adresse.

    Les Pods sont relus à chaque appel : un Pod recréé entre deux tours ne doit
    pas être désigné comme fautif alors qu'il n'existait déjà plus.
    """
    reponses: dict[str, str] = {}
    for pod in _pods_prets(host, couleur):
        nom = f"{pod['metadata']['name']} ({pod['status']['podIP']})"
        res = _requete(host, f"http://{pod['status']['podIP']}:{PORT}/")
        if res.rc != 0:
            reponses[nom] = "no answer"
        else:
            reponses[nom] = res.stdout.strip()
    return reponses


# ----------------------------------------------------------------------
# 1. app-blue : deux replicas, les labels, et sa version servie.
# ----------------------------------------------------------------------
def _deux_replicas(host, couleur: str) -> None:
    deployment = _deployment(host, couleur)
    fin = time.monotonic() + ATTENTE
    while deployment is not None and time.monotonic() < fin:
        if deployment["status"].get("availableReplicas", 0) == 2:
            break
        time.sleep(PAS)
        deployment = _deployment(host, couleur)
    assert deployment is not None, message(
        en=f"No Deployment app-{couleur} in {NAMESPACE}.",
        fr=f"Aucun Deployment app-{couleur} dans {NAMESPACE}.",
    )
    demandes = deployment["spec"].get("replicas")
    assert demandes == 2, message(
        en=f"app-{couleur} asks for {demandes} replica(s), expected 2.",
        fr=f"app-{couleur} demande {demandes} replica(s), attendu 2.",
    )
    disponibles = deployment["status"].get("availableReplicas", 0)
    assert disponibles == 2, message(
        en=f"app-{couleur}: {disponibles} replica(s) available out of 2 after "
        f"{ATTENTE}s. Its Pods say why: look at their phase and their events.",
        fr=f"app-{couleur} : {disponibles} replica(s) disponible(s) sur 2 après "
        f"{ATTENTE}s. Ses Pods disent pourquoi : regarde leur phase et leurs events.",
    )


def _labels_de_version(host, couleur: str) -> None:
    pods = _pods(host, couleur)
    assert len(pods) >= 2, message(
        en=f"{len(pods)} Pod(s) carry both app={APPLICATION} and version={couleur}, "
        "expected 2. Those labels are the Pods' labels, so the ones in the "
        "Deployment's template, and they are what a Service selects.",
        fr=f"{len(pods)} Pod(s) portent à la fois app={APPLICATION} et "
        f"version={couleur}, attendu 2. Ces labels sont ceux des Pods, donc ceux "
        "du template du Deployment, et ce sont eux qu'un Service sélectionne.",
    )


def _sert_sa_version(host, couleur: str) -> None:
    reponses = _reponses_des_pods(host, couleur)
    fin = time.monotonic() + ATTENTE
    while time.monotonic() < fin:
        if reponses and all(r == couleur for r in reponses.values()):
            break
        time.sleep(PAS)
        reponses = _reponses_des_pods(host, couleur)
    assert reponses, message(
        en=f"No ready Pod of version {couleur} has an address to query.",
        fr=f"Aucun Pod prêt de la version {couleur} n'a d'adresse à interroger.",
    )
    fautifs = {nom: r for nom, r in reponses.items() if r != couleur}
    assert not fautifs, message(
        en=f"Queried on port {PORT}, the Pods of version {couleur} answer "
        f"{fautifs}, expected {couleur!r} from each. A container that only sleeps "
        f"carries the right labels and serves nothing: the {couleur} version must "
        "stay standing AND serving, because that is what makes the rollback "
        "instant.",
        fr=f"Interrogés sur le port {PORT}, les Pods de la version {couleur} "
        f"répondent {fautifs}, attendu {couleur!r} de chacun. Un conteneur qui ne "
        "fait que dormir porte les bons labels et ne sert rien : la version "
        f"{couleur} doit rester debout ET servante, car c'est ce qui rend le "
        "retour arrière instantané.",
    )


def test_blue_tourne_en_deux_replicas(host):
    _deux_replicas(host, "blue")


def test_blue_porte_les_labels_de_version(host):
    _labels_de_version(host, "blue")


def test_blue_sert_sa_version(host, client):
    _sert_sa_version(host, "blue")


# ----------------------------------------------------------------------
# 2. app-green : les trois mêmes états.
# ----------------------------------------------------------------------
def test_green_tourne_en_deux_replicas(host):
    _deux_replicas(host, "green")


def test_green_porte_les_labels_de_version(host):
    _labels_de_version(host, "green")


def test_green_sert_sa_version(host, client):
    _sert_sa_version(host, "green")


# ----------------------------------------------------------------------
# 3. Le Service : son port, son selector, ses endpoints.
# ----------------------------------------------------------------------
def _service(host) -> dict:
    return _json(host, f"-n {NAMESPACE} get service {SERVICE}", message(
        en=f"No Service {SERVICE} in {NAMESPACE}.",
        fr=f"Aucun Service {SERVICE} dans {NAMESPACE}.",
    ))


def test_le_service_ecoute_sur_8080(host):
    ports = [p.get("port") for p in _service(host)["spec"].get("ports") or []]
    assert PORT in ports, message(
        en=f"{SERVICE} does not listen on {PORT}: ports {ports}. The learner "
        f"queries http://{SERVICE}:{PORT}/, so that is the Service's port, which "
        "is not necessarily the container's.",
        fr=f"{SERVICE} n'écoute pas sur {PORT} : ports {ports}. L'apprenant "
        f"interroge http://{SERVICE}:{PORT}/, c'est donc le port du Service, qui "
        "n'est pas forcément celui du conteneur.",
    )


def test_le_selector_vise_la_version_green(host):
    selecteur = _service(host)["spec"].get("selector") or {}
    assert selecteur.get("version") == "green", message(
        en=f"The selector of {SERVICE} is {selecteur}: it does not designate the "
        "green version. One field of the Service decides which version receives "
        "the traffic, and the statement says which two labels it must name.",
        fr=f"Le selector de {SERVICE} vaut {selecteur} : il ne désigne pas la "
        "version green. Un champ du Service décide quelle version reçoit le "
        "trafic, et l'énoncé dit quels deux labels il doit nommer.",
    )
    assert selecteur.get("app") == APPLICATION, message(
        en=f"The selector of {SERVICE} is {selecteur}: it does not name "
        f"app={APPLICATION}, which the statement asks for. Without it, the Service "
        "could target the Pods of another application that happens to carry the "
        "same version label.",
        fr=f"Le selector de {SERVICE} vaut {selecteur} : il ne nomme pas "
        f"app={APPLICATION}, que l'énoncé demande. Sans lui, le Service pourrait "
        "viser les Pods d'une autre application qui porterait le même label de "
        "version.",
    )


def test_les_endpoints_sont_exactement_les_pods_green(host):
    adresses: set[str] = set()
    green: set[str] = set()
    blue: set[str] = set()
    fin = time.monotonic() + ATTENTE
    while True:
        # Les endpoints d'abord, les Pods ensuite : un Pod apparu entre les deux
        # lectures se retrouve dans la seconde, donc jamais compté comme une
        # adresse inattendue. Les deux ensembles sont relus à chaque tour.
        adresses = _endpoints(host)
        green = _adresses(host, "green")
        blue = _adresses(host, "blue")
        if adresses and adresses == green and not (adresses & blue):
            break
        if time.monotonic() >= fin:
            break
        time.sleep(PAS)
    assert adresses, message(
        en=f"{SERVICE} has no ready endpoint after {ATTENTE}s: it selects no Pod "
        "that is up, or the Pods it selects are not ready.",
        fr=f"{SERVICE} n'a aucun endpoint prêt après {ATTENTE}s : il ne sélectionne "
        "aucun Pod debout, ou les Pods qu'il sélectionne ne sont pas prêts.",
    )
    assert not (adresses & blue), message(
        en=f"Endpoints of {SERVICE} are still blue Pods: {sorted(adresses & blue)}. "
        "The switch is only done when the old version receives nothing more. The "
        "endpoint list of a Service is readable, and it says which Pods it really "
        "targets, whatever its selector looks like.",
        fr=f"Des endpoints de {SERVICE} sont encore des Pods blue : "
        f"{sorted(adresses & blue)}. La bascule n'est faite que quand l'ancienne "
        "version ne reçoit plus rien. La liste des endpoints d'un Service se lit, "
        "et elle dit quels Pods il vise réellement, quelle que soit l'allure de "
        "son selector.",
    )
    assert adresses <= green, message(
        en=f"Endpoints of {SERVICE} that are no green Pod: "
        f"{sorted(adresses - green)}. Green Pods read at the same moment: "
        f"{sorted(green)}.",
        fr=f"Des endpoints de {SERVICE} ne sont aucun Pod green : "
        f"{sorted(adresses - green)}. Pods green relus au même instant : "
        f"{sorted(green)}.",
    )
    assert green <= adresses, message(
        en=f"Ready green Pods that {SERVICE} does not target: "
        f"{sorted(green - adresses)}. The endpoints must be exactly the green "
        "Pods, so all of them.",
        fr=f"Des Pods green prêts ne sont pas visés par {SERVICE} : "
        f"{sorted(green - adresses)}. Les endpoints doivent être exactement les "
        "Pods green, donc tous.",
    )


# ----------------------------------------------------------------------
# 4. La preuve, depuis le client : toutes les requêtes atteignent green.
# ----------------------------------------------------------------------
def test_toutes_les_requetes_atteignent_green(host, client):
    cible = f"http://{SERVICE}:{PORT}/"
    # Attente propre à ce test : la convergence des endpoints prend quelques
    # secondes après un changement de selector, et ce test doit tenir joué seul.
    fin = time.monotonic() + ATTENTE
    while time.monotonic() < fin:
        premiere = _requete(host, cible)
        if premiere.rc == 0 and premiere.stdout.strip() == "green":
            break
        time.sleep(PAS)
    reponses = []
    for _ in range(6):
        res = _requete(host, cible)
        if res.rc != 0:
            reponses.append("no answer")
        else:
            reponses.append(res.stdout.strip())
    assert all(r == "green" for r in reponses), message(
        en=f"Out of six requests to {cible} from {CLIENT}, the answers are "
        f"{reponses}. As long as a single one is not 'green', the switch is not "
        "complete: a Service that still selects both versions balances across "
        "them, and 'no answer' means it sends to a Pod that serves nothing.",
        fr=f"Sur six requêtes vers {cible} depuis {CLIENT}, les réponses sont "
        f"{reponses}. Tant qu'une seule n'est pas 'green', la bascule n'est pas "
        "complète : un Service qui sélectionne encore les deux versions répartit "
        "entre elles, et 'no answer' signifie qu'il envoie vers un Pod qui ne sert "
        "rien.",
    )
