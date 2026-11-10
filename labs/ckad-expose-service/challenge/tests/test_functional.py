"""test_functional.py : ckad-expose-service

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées, et jamais un
fichier YAML du poste.

Un test par état demandé par l'énoncé, onze en tout. Les quatre premiers lisent
le Deployment et les Pods qu'il a réellement produits, les quatre suivants le
Service et ses endpoints, les trois derniers font des requêtes depuis le Pod
`client` et prouvent l'effet : un selector qui n'attrape qu'un Pod, ou un
conteneur qui sert un nom qui n'est pas le sien, passeraient les premiers.

Deux points de méthode qui tiennent la mesure honnête :

- la preuve « chaque Pod répond son propre nom » compare les réponses à la
  LISTE RÉELLE des Pods, puis interroge chaque Pod sur sa propre boucle locale
  et exige qu'il serve SON nom. Un conteneur qui écrirait un identifiant
  inventé dans son index.html donnerait des réponses distinctes préfixées
  `web-` sans jamais servir son nom d'hôte : c'est refusé ici ;
- les boucles d'attente ne vivent que dans deux tests, « les trois replicas
  sont disponibles » et « trois endpoints prêts ». Les autres lisent un état
  déjà stabilisé par ces deux-là, et un `check` ne paie donc l'attente qu'une
  fois. Les dix requêtes HTTP sont faites une seule fois, par une fixture de
  portée module, et les trois derniers tests les relisent.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
DEPLOYMENT = "web"
SERVICE = "web-svc"
CLIENT = "client"
IMAGE = "busybox:1.36"
LABEL = "app=web"
REPLICAS = 3
PORT_SERVICE = 80
PORT_CIBLE = 8080
REQUETES = 10
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


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
    """Le Deployment web, lu dans le cluster. Sans boucle d'attente : les tests
    qui attendent sont nommés, et ce sont les seuls à payer ce prix."""
    return _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", message(
        en=f"No Deployment {DEPLOYMENT} in namespace {NAMESPACE}. "
        f"Check with: kubectl -n {NAMESPACE} get deployments",
        fr=f"Aucun Deployment {DEPLOYMENT} dans le namespace {NAMESPACE}. "
        f"À vérifier avec : kubectl -n {NAMESPACE} get deployments",
    ))


def _service(host) -> dict:
    """Le Service web-svc, lu dans le cluster."""
    return _json(host, f"-n {NAMESPACE} get service {SERVICE}", message(
        en=f"No Service {SERVICE} in namespace {NAMESPACE}. "
        f"Check with: kubectl -n {NAMESPACE} get services",
        fr=f"Aucun Service {SERVICE} dans le namespace {NAMESPACE}. "
        f"À vérifier avec : kubectl -n {NAMESPACE} get services",
    ))


def _pods_web(host) -> list[dict]:
    """Les Pods RÉELLEMENT présents qui portent le label app=web.

    Rend une liste vide si la lecture échoue : chaque test donne alors son
    propre message, plutôt que de recevoir celui d'un helper partagé.
    """
    res = _kubectl(host, f"-n {NAMESPACE} get pods -l {LABEL} -o json")
    if res.rc != 0:
        return []
    return json.loads(res.stdout).get("items") or []


def _noms_de_pods(pods: list[dict]) -> set[str]:
    return {p["metadata"]["name"] for p in pods}


def _pods_vivants(pods: list[dict]) -> list[dict]:
    """Les Pods que l'on peut interroger : en marche, et pas en train de partir.

    Un Pod d'une tentative précédente, encore visible le temps de sa
    terminaison, n'a pas à faire rougir un critère : il ne sert plus rien et il
    va disparaître. Il reste en revanche compté dans les NOMS connus, parce
    qu'il a pu répondre à une requête juste avant.
    """
    return [
        pod for pod in pods
        if pod["metadata"].get("deletionTimestamp") is None
        and pod["status"].get("phase") == "Running"
    ]


def _pods_etrangers(pods: list[dict]) -> list[str]:
    """Les Pods étiquetés app=web que le Deployment web ne gère pas.

    Un Pod posé à la main avec ce label entre dans le Service et fait passer
    les endpoints prêts à plus de trois. Le nommer, c'est dire quoi retirer.
    """
    etrangers = []
    for pod in pods:
        refs = pod["metadata"].get("ownerReferences") or []
        gere = any(
            ref.get("kind") == "ReplicaSet"
            and str(ref.get("name", "")).startswith(f"{DEPLOYMENT}-")
            for ref in refs
        )
        if not gere:
            etrangers.append(pod["metadata"]["name"])
    return sorted(etrangers)


def _ports_cibles_nommes(pods: list[dict]) -> set[str]:
    """Les noms de containerPort qui désignent le port 8080 dans les Pods.

    L'énoncé demande que le Service vise le port 8080 des Pods. Le viser par
    son numéro ou par le nom d'un containerPort qui vaut 8080 décrit le même
    état : les deux écritures sont acceptées.
    """
    noms = set()
    for pod in pods:
        for conteneur in pod["spec"].get("containers") or []:
            for port in conteneur.get("ports") or []:
                if port.get("containerPort") == PORT_CIBLE and port.get("name"):
                    noms.add(port["name"])
    return noms


@pytest.fixture(scope="module")
def sondage(host) -> dict:
    """Dix requêtes depuis le client, faites UNE SEULE FOIS pour trois tests.

    Aucune assertion ici : une fixture qui échoue rend une erreur de
    préparation, pas un critère non satisfait. Elle ne fait que constater, et
    distingue trois situations que les tests jugent ensuite : le client a
    disparu, le client est là mais le Service ne répond pas, le Service
    répond.
    """
    present = _kubectl(host, f"-n {NAMESPACE} get pod {CLIENT} -o name").rc == 0
    reponses: list[str] = []
    echecs: list[str] = []
    if present:
        for _ in range(REQUETES):
            res = _kubectl(
                host,
                f"-n {NAMESPACE} exec {CLIENT} -- wget -qO- -T 5 http://{SERVICE}/",
            )
            if res.rc == 0:
                reponses.append(res.stdout.strip())
            else:
                echecs.append(((res.stderr or res.stdout) or "").strip()[:150])
    return {"client_present": present, "reponses": reponses, "echecs": echecs}


# ----------------------------------------------------------------------
# 1 à 4. Le Deployment, et les Pods qu'il a réellement produits.
# ----------------------------------------------------------------------
def test_le_deployment_demande_trois_replicas(host):
    demande = _deployment(host)["spec"].get("replicas")
    assert demande == REPLICAS, message(
        en=f"Deployment {DEPLOYMENT} asks for {demande} replica(s), expected {REPLICAS}. "
        "The number of replicas is a field of the Deployment, not a property of the Pods.",
        fr=f"Le Deployment {DEPLOYMENT} demande {demande} replica(s), attendu {REPLICAS}. "
        "Le nombre de replicas est un champ du Deployment, pas une propriété des Pods.",
    )


def test_les_trois_replicas_sont_disponibles(host):
    """Le seul test qui attend que le Deployment converge, avec celui des
    endpoints. Les suivants lisent l'état qu'il a stabilisé."""
    deployment: dict = {}
    for _ in range(12):
        deployment = _deployment(host)
        if deployment["status"].get("availableReplicas", 0) == REPLICAS:
            break
        time.sleep(5)
    disponibles = deployment["status"].get("availableReplicas", 0)
    assert disponibles == REPLICAS, message(
        en=f"{disponibles} replica(s) available out of {REPLICAS} after one minute of waiting. "
        f"The events of the Pods say why: kubectl -n {NAMESPACE} get pods -l {LABEL}, "
        f"then kubectl -n {NAMESPACE} describe pod <name>. A container whose command "
        "exits right away restarts in a loop and never becomes available.",
        fr=f"{disponibles} replica(s) disponible(s) sur {REPLICAS} après une minute "
        f"d'attente. Les events des Pods disent pourquoi : "
        f"kubectl -n {NAMESPACE} get pods -l {LABEL}, puis "
        f"kubectl -n {NAMESPACE} describe pod <nom>. Un conteneur dont la commande se "
        "termine aussitôt redémarre en boucle et ne devient jamais disponible.",
    )


def test_les_pods_portent_le_label_app_web(host):
    labels = _deployment(host)["spec"]["template"]["metadata"].get("labels") or {}
    assert labels.get("app") == "web", message(
        en=f"The Pod template of {DEPLOYMENT} carries the labels {labels}, which do not "
        f"include {LABEL}. That is the label the Service selects: without it, the Service "
        "finds nothing, whatever its own definition says.",
        fr=f"Le template de Pod de {DEPLOYMENT} porte les labels {labels}, qui ne "
        f"contiennent pas {LABEL}. C'est ce label que le Service sélectionne : sans lui, "
        "le Service ne trouve rien, quelle que soit sa propre définition.",
    )
    pods = _pods_web(host)
    assert len(pods) >= REPLICAS, message(
        en=f"{len(pods)} Pod(s) carry {LABEL} in {NAMESPACE}, expected at least {REPLICAS}. "
        "The template declares the label, but the Pods in place do not carry it: they are "
        "probably left over from an earlier attempt.",
        fr=f"{len(pods)} Pod(s) portent {LABEL} dans {NAMESPACE}, attendu au moins {REPLICAS}. "
        "Le template déclare le label, mais les Pods en place ne le portent pas : ils "
        "viennent probablement d'une tentative précédente.",
    )


def test_les_pods_tournent_avec_l_image_demandee(host):
    pods = _pods_vivants(_pods_web(host))
    assert pods, message(
        en=f"No running Pod carries {LABEL} in {NAMESPACE}: the image cannot be read. "
        "Start with the Deployment and its label.",
        fr=f"Aucun Pod en marche ne porte {LABEL} dans {NAMESPACE} : l'image ne peut pas "
        "être lue. Commencer par le Deployment et son label.",
    )
    ecarts = sorted({
        f"{pod['metadata']['name']}: {conteneur.get('image')!r}"
        for pod in pods
        for conteneur in pod["spec"].get("containers") or []
        if conteneur.get("image") != IMAGE
    })
    assert not ecarts, message(
        en=f"The Pods of {DEPLOYMENT} must run image {IMAGE!r}. Found: {ecarts}. "
        "The exercise is to make a minimal container serve its hostname, not to use a "
        "web server that already serves a page.",
        fr=f"Les Pods de {DEPLOYMENT} doivent tourner avec l'image {IMAGE!r}. Relevé : {ecarts}. "
        "L'exercice est de faire servir son nom d'hôte par un conteneur minimal, pas "
        "d'utiliser un serveur web qui sert déjà une page.",
    )


# ----------------------------------------------------------------------
# 5 à 8. Le Service : son type, ses ports, son selector, ses endpoints.
# ----------------------------------------------------------------------
def test_le_service_est_de_type_clusterip(host):
    type_reel = _service(host)["spec"].get("type", "ClusterIP")
    assert type_reel == "ClusterIP", message(
        en=f"Service {SERVICE} is of type {type_reel!r}, expected 'ClusterIP'. "
        "The Service must be reachable from inside the cluster only; nothing is to be "
        "published outside.",
        fr=f"Le Service {SERVICE} est de type {type_reel!r}, attendu 'ClusterIP'. "
        "Le Service doit être joignable depuis l'intérieur du cluster seulement ; rien "
        "n'est à publier vers l'extérieur.",
    )


def test_le_service_ecoute_sur_80_vers_8080(host):
    ports = _service(host)["spec"].get("ports") or []
    sur_80 = [p for p in ports if p.get("port") == PORT_SERVICE]
    assert sur_80, message(
        en=f"Service {SERVICE} does not listen on port {PORT_SERVICE}. Its ports: {ports}. "
        "The port the clients call and the port the container serves are two different "
        "fields.",
        fr=f"Le Service {SERVICE} n'écoute pas sur le port {PORT_SERVICE}. Ses ports : {ports}. "
        "Le port que les clients appellent et le port que le conteneur sert sont deux "
        "champs différents.",
    )
    nommes = _ports_cibles_nommes(_pods_vivants(_pods_web(host)))
    cibles = [p.get("targetPort") for p in sur_80]
    accepte = any(
        str(cible) == str(PORT_CIBLE) or (isinstance(cible, str) and cible in nommes)
        for cible in cibles
    )
    assert accepte, message(
        en=f"Port {PORT_SERVICE} of {SERVICE} targets {cibles}, which does not resolve to "
        f"port {PORT_CIBLE} of the Pods. The number {PORT_CIBLE} is accepted, and so is the "
        f"name of a containerPort equal to {PORT_CIBLE} (named ports found: {sorted(nommes)}).",
        fr=f"Le port {PORT_SERVICE} de {SERVICE} vise {cibles}, ce qui ne désigne pas le "
        f"port {PORT_CIBLE} des Pods. Le numéro {PORT_CIBLE} est accepté, et le nom d'un "
        f"containerPort qui vaut {PORT_CIBLE} l'est aussi (ports nommés relevés : "
        f"{sorted(nommes)}).",
    )


def test_le_service_selectionne_app_web(host):
    selector = _service(host)["spec"].get("selector") or {}
    assert selector.get("app") == "web", message(
        en=f"The selector of {SERVICE} is {selector}, expected {LABEL}. A Service finds its "
        "Pods by their labels, never by the name of the Deployment.",
        fr=f"Le selector de {SERVICE} vaut {selector}, attendu {LABEL}. Un Service trouve "
        "ses Pods par leurs labels, jamais par le nom du Deployment.",
    )


def test_le_service_a_trois_endpoints_prets(host):
    """Le second et dernier test qui attend. Les endpoints apparaissent après
    les Pods, et c'est cette attente que les tests de requêtes n'ont plus à
    payer."""
    prets: list[str] = []
    for _ in range(12):
        tranches = _json(
            host,
            f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}",
            message(
                en=f"Cannot read the EndpointSlices of {SERVICE}.",
                fr=f"Lecture des EndpointSlices de {SERVICE} impossible.",
            ),
        )
        prets = [
            adresse
            for tranche in tranches["items"]
            for endpoint in tranche.get("endpoints") or []
            for adresse in endpoint.get("addresses") or []
            if (endpoint.get("conditions") or {}).get("ready")
        ]
        if len(prets) == REPLICAS:
            break
        time.sleep(5)
    if len(prets) > REPLICAS:
        etrangers = _pods_etrangers(_pods_vivants(_pods_web(host)))
        assert not etrangers, message(
            en=f"{SERVICE} has {len(prets)} ready endpoints, expected exactly {REPLICAS}. "
            f"These Pods carry {LABEL} without being managed by Deployment {DEPLOYMENT}, "
            f"so the Service picks them up too: {etrangers}. Remove them with "
            f"kubectl -n {NAMESPACE} delete pod {' '.join(etrangers)}",
            fr=f"{SERVICE} a {len(prets)} endpoints prêts, attendu exactement {REPLICAS}. "
            f"Ces Pods portent {LABEL} sans être gérés par le Deployment {DEPLOYMENT}, "
            f"le Service les prend donc aussi : {etrangers}. Les retirer avec "
            f"kubectl -n {NAMESPACE} delete pod {' '.join(etrangers)}",
        )
    assert len(prets) == REPLICAS, message(
        en=f"{SERVICE} has {len(prets)} ready endpoint(s), expected exactly {REPLICAS}. "
        f"Below {REPLICAS}, the selector catches fewer Pods than the Deployment runs, or "
        f"some Pods are not ready. Above {REPLICAS}, another Pod carries {LABEL}. "
        f"To see: kubectl -n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}",
        fr=f"{SERVICE} a {len(prets)} endpoint(s) prêt(s), attendu exactement {REPLICAS}. "
        f"En dessous de {REPLICAS}, le selector attrape moins de Pods que le Deployment "
        f"n'en fait tourner, ou des Pods ne sont pas prêts. Au-dessus de {REPLICAS}, un "
        f"autre Pod porte {LABEL}. Pour voir : "
        f"kubectl -n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}",
    )


# ----------------------------------------------------------------------
# 9 à 11. La preuve, depuis le client : par son nom, son propre nom, réparti.
# ----------------------------------------------------------------------
def test_le_service_repond_sous_son_nom_depuis_le_client(sondage):
    assert sondage["client_present"], message(
        en=f"The Pod {CLIENT} no longer exists in {NAMESPACE}. It is the lab's measuring "
        "instrument, not part of the work to be done, and without it nothing can be "
        "queried. Put it back with: dsoxlab reset ckad-expose-service",
        fr=f"Le Pod {CLIENT} n'existe plus dans {NAMESPACE}. C'est l'instrument de mesure "
        "du lab, pas une partie du travail à faire, et sans lui rien ne peut être "
        "interrogé. Le remettre avec : dsoxlab reset ckad-expose-service",
    )
    assert not sondage["echecs"], message(
        en=f"{len(sondage['echecs'])} request(s) out of {REQUETES} failed from {CLIENT} "
        f"towards http://{SERVICE}/ : {sorted(set(sondage['echecs']))}. The name resolves "
        "through the cluster DNS inside the namespace; a Service with no ready endpoint "
        "resolves and then refuses the connection.",
        fr=f"{len(sondage['echecs'])} requête(s) sur {REQUETES} ont échoué depuis {CLIENT} "
        f"vers http://{SERVICE}/ : {sorted(set(sondage['echecs']))}. Le nom se résout par "
        "le DNS du cluster dans le namespace ; un Service sans endpoint prêt se résout "
        "puis refuse la connexion.",
    )


def test_chaque_pod_repond_son_propre_nom(host, sondage):
    pods = _pods_web(host)
    noms = _noms_de_pods(pods)
    assert noms, message(
        en=f"No Pod carries {LABEL} in {NAMESPACE}: there is no real name to compare the "
        "answers against.",
        fr=f"Aucun Pod ne porte {LABEL} dans {NAMESPACE} : il n'y a aucun nom réel auquel "
        "comparer les réponses.",
    )
    assert sondage["reponses"], message(
        en=f"No answer was collected from {CLIENT}: the previous criterion says why.",
        fr=f"Aucune réponse n'a été recueillie depuis {CLIENT} : le critère précédent dit "
        "pourquoi.",
    )
    inconnues = sorted({r for r in sondage["reponses"] if r not in noms})
    assert not inconnues, message(
        en=f"The Service answered {inconnues}, which are not names of Pods present in "
        f"{NAMESPACE}. The Pods really in place are {sorted(noms)}. Each Pod must serve "
        "ITS OWN hostname, not a value it makes up.",
        fr=f"Le Service a répondu {inconnues}, qui ne sont pas des noms de Pods présents "
        f"dans {NAMESPACE}. Les Pods réellement en place sont {sorted(noms)}. Chaque Pod "
        "doit servir SON PROPRE nom d'hôte, pas une valeur qu'il invente.",
    )
    interrogeables = sorted(_noms_de_pods(_pods_vivants(pods)))
    assert interrogeables, message(
        en=f"No Pod carrying {LABEL} is running: there is nothing to query, so the proof "
        "cannot be made. A vacuous check would pass without measuring anything.",
        fr=f"Aucun Pod portant {LABEL} n'est en marche : il n'y a rien à interroger, donc "
        "la preuve ne peut pas être faite. Un contrôle à vide passerait sans rien mesurer.",
    )
    menteurs = []
    for nom in interrogeables:
        res = _kubectl(
            host,
            f"-n {NAMESPACE} exec {nom} -- wget -qO- -T 5 http://127.0.0.1:{PORT_CIBLE}/",
        )
        servi = res.stdout.strip()
        if res.rc != 0 or servi != nom:
            detail = servi or ((res.stderr or "").strip())
            menteurs.append(f"{nom} -> {detail[:60]!r}")
    assert not menteurs, message(
        en=f"Queried on its own 127.0.0.1:{PORT_CIBLE}, each Pod must answer its own name. "
        f"Mismatches: {menteurs}. Inside a Pod, the hostname is the Pod name, and the "
        "container must read it rather than hold a fixed or random value.",
        fr=f"Interrogé sur son propre 127.0.0.1:{PORT_CIBLE}, chaque Pod doit répondre son "
        f"propre nom. Écarts : {menteurs}. Dans un Pod, le nom d'hôte est le nom du Pod, "
        "et le conteneur doit le lire plutôt que porter une valeur fixe ou tirée au "
        "hasard.",
    )


def test_le_service_repartit_entre_plusieurs_pods(sondage):
    reponses = sondage["reponses"]
    distinctes = sorted(set(reponses))
    assert len(distinctes) >= 2, message(
        en=f"{len(reponses)} answer(s) collected over {REQUETES} requests, {len(distinctes)} "
        f"distinct Pod(s): {distinctes}. A ClusterIP Service spreads the connections over "
        "all its ready endpoints; a single answering Pod means only one stands behind it.",
        fr=f"{len(reponses)} réponse(s) recueillie(s) sur {REQUETES} requêtes, "
        f"{len(distinctes)} Pod(s) distinct(s) : {distinctes}. Un Service ClusterIP "
        "répartit les connexions sur tous ses endpoints prêts ; un seul Pod qui répond "
        "signifie qu'un seul est derrière lui.",
    )
