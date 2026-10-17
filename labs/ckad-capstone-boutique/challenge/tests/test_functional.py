"""test_functional.py : ckad-capstone-boutique

Dix affirmations, une par point de mesure, qui lisent l'état du CLUSTER et
jamais les commandes tapées. Le cahier des charges ne nomme aucun objet : ces
tests ne peuvent donc pas vérifier « le bon YAML », seulement le RÉSULTAT.

Un capstone se mesure autrement qu'un micro-lab. Un micro-lab enseigne un
geste et peut se contenter de lire une spec ; ici le candidat compose six
exigences, et une spec conforme qui ne produit pas l'effet attendu ne vaut
rien. Chaque fois que c'est possible, on entre donc dans le conteneur pour
voir ce qu'il reçoit vraiment, plutôt que de relire ce que le manifeste
promet. Les deux derniers tests sont les seuls qui prouvent l'isolation, et
ils la prouvent dans les deux sens : ce qui doit passer et ce qui doit être
bloqué.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "boutique"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
DEPLOIEMENT = "catalogue"
SERVICE = "catalogue-svc"
CONFIG = "catalogue-config"
SECRET = "catalogue-db"  # noqa: S105 - nom d'un Secret, pas un mot de passe
MESSAGE = "Bienvenue dans la boutique"
MOT_DE_PASSE = "s3cr3t-boutique"
UID_ATTENDU = "101"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Joue une commande kubectl sur le control plane.

    Rend (code, sortie standard, diagnostic), et les trois restent SÉPARÉS.
    Concaténer stdout et stderr a déjà coûté un lab au catalogue : le client
    SSH écrit un avertissement sur stderr, la chaîne n'est donc jamais vide,
    et un test qui conclut « chaîne vide = absent » conclut toujours
    « présent ». Il passait avant le travail.
    """
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _json(host, args: str, quoi: str) -> dict:
    rc, sortie, diagnostic = _kubectl(host, f"{args} -o json")
    assert rc == 0 and sortie, message(
        en=f"{quoi} does not exist in namespace {NAMESPACE}. The specification "
        f"names it explicitly: the name is part of the delivery, "
        f"it is not a matter of choice. Output: {diagnostic}",
        fr=f"{quoi} n'existe pas dans le namespace {NAMESPACE}. Le cahier des "
        f"charges le nomme explicitement : le nom fait partie de la livraison, "
        f"il n'est pas au choix. Sortie : {diagnostic}",
    )
    return json.loads(sortie)


def _selecteur(host) -> str:
    """Le sélecteur de labels des Pods du catalogue, lu dans le Deployment.

    Il est LU, jamais deviné. Le cahier des charges ne dit pas quels labels
    employer, seulement quel nom porte la livraison : un test qui chercherait
    `-l app=catalogue` mesurerait la conformité à une convention que personne
    n'a demandée, et rendrait ROUGE une livraison correcte.
    """
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT}", f"Le Deployment {DEPLOIEMENT}")
    labels = (d["spec"].get("selector") or {}).get("matchLabels") or {}
    assert labels, message(
        en=f"Deployment {DEPLOIEMENT} has no selector matchLabels: "
        "there is no way to find its Pods.",
        fr=f"Le Deployment {DEPLOIEMENT} n'a pas de selector matchLabels : "
        "impossible de retrouver ses Pods.",
    )
    return ",".join(f"{cle}={valeur}" for cle, valeur in sorted(labels.items()))


def _un_pod(host) -> str:
    """Le nom d'un des Pods du catalogue, pour aller voir de l'intérieur."""
    rc, nom, _ = _kubectl(
        host,
        f"-n {NAMESPACE} get pods -l {_selecteur(host)} "
        "--field-selector=status.phase=Running "
        "-o jsonpath='{.items[0].metadata.name}'",
    )
    assert rc == 0 and nom, message(
        en="No catalogue Pod is running in the boutique namespace. The frontend "
        "and intrus Pods do not count: they were already there, they are not "
        "the delivery.",
        fr="Aucun Pod du catalogue ne tourne dans le namespace boutique. Les Pods "
        "frontend et intrus ne comptent pas : ils étaient déjà là, ils ne sont "
        "pas la livraison.",
    )
    return nom


def _dans_le_conteneur(host, commande: str):
    pod = _un_pod(host)
    return _kubectl(
        host, f"-n {NAMESPACE} exec {pod} --request-timeout=30s -- {commande}"
    )


def _joint_la_boutique(host, depuis: str) -> tuple[bool, str]:
    """Une requête HTTP depuis un Pod client vers le nom stable du service.

    Passe par le NOM et non par une adresse : c'est l'exigence 6 telle qu'elle
    est écrite, et cela éprouve du même coup la résolution et le Service.
    """
    rc, _, diagnostic = _kubectl(
        host,
        f"-n {NAMESPACE} exec {depuis} --request-timeout=30s -- "
        f"wget -qO- -T 5 http://{SERVICE}/",
    )
    return rc == 0, diagnostic


# ----------------------------------------------------------------------
# Exigence 1. Deux exemplaires, et ils tiennent debout.
# ----------------------------------------------------------------------
def test_le_catalogue_tourne_en_deux_exemplaires(host):
    """Un objet qui remplace un exemplaire disparu, et deux exemplaires prêts.

    On lit `readyReplicas` et non `replicas` : un Deployment qui demande deux
    copies dont aucune ne démarre annonce quand même 2 en souhaité.
    """
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT}", f"Le Deployment {DEPLOIEMENT}")
    souhaite = d["spec"].get("replicas")
    assert souhaite == 2, message(
        en=f"The catalogue asks for {souhaite} replica(s); the specification "
        "asks for two.",
        fr=f"Le catalogue demande {souhaite} exemplaire(s), le cahier des charges "
        "en demande deux.",
    )
    prets = d.get("status", {}).get("readyReplicas", 0)
    assert prets == 2, message(
        en=f"{prets} replica(s) out of 2 are ready. Look at the namespace's events "
        "and at a Pod's logs: a missing image, an impossible mount "
        "or an over-impatient probe keeps a Pod from becoming ready.",
        fr=f"{prets} exemplaire(s) sur 2 sont prêts. Regardez les events du "
        "namespace et les logs d'un Pod : une image absente, un montage "
        "impossible ou une sonde trop impatiente empêchent un Pod de le devenir.",
    )


# ----------------------------------------------------------------------
# Exigence 2. La configuration vit dehors, et arrive dedans.
# ----------------------------------------------------------------------
def test_le_message_vit_en_dehors_du_pod(host):
    """L'objet existe et porte le texte. Sans lui, la variable serait en dur."""
    cm = _json(host, f"-n {NAMESPACE} get configmap {CONFIG}", f"L'objet {CONFIG}")
    valeurs = list((cm.get("data") or {}).values())
    assert MESSAGE in valeurs, message(
        en=f"Object {CONFIG} does not contain the expected text. It carries "
        f"{valeurs or 'no data'}, and the specification asks for "
        f"\"{MESSAGE}\".",
        fr=f"L'objet {CONFIG} ne contient pas le texte attendu. Il porte "
        f"{valeurs or 'aucune donnée'}, et le cahier des charges demande "
        f"« {MESSAGE} ».",
    )


def test_le_conteneur_recoit_vraiment_le_message(host):
    """La preuve, prise DANS le conteneur.

    Un `envFrom` mal nommé, une clé absente ou un Pod jamais redéployé après
    la correction donnent tous une spec plausible et un conteneur sans
    variable. Seul `printenv` tranche.
    """
    rc, sortie, diagnostic = _dans_le_conteneur(host, "printenv MESSAGE")
    assert rc == 0 and sortie, message(
        en="The MESSAGE variable does not exist in the container. It must be "
        f"injected there from {CONFIG}, and a Pod that has already started will "
        f"not receive it retroactively: it has to be replaced. Output: {diagnostic}",
        fr="La variable MESSAGE n'existe pas dans le conteneur. Elle doit y être "
        f"injectée depuis {CONFIG}, et un Pod déjà démarré ne la recevra pas "
        f"rétroactivement : il faut le remplacer. Sortie : {diagnostic}",
    )
    assert sortie == MESSAGE, message(
        en=f"The container receives \"{sortie}\"; the specification asks for "
        f"\"{MESSAGE}\".",
        fr=f"Le conteneur reçoit « {sortie} », le cahier des charges demande "
        f"« {MESSAGE} ».",
    )


# ----------------------------------------------------------------------
# Exigence 3. Le mot de passe est détenu ailleurs, et lu en fichier.
# ----------------------------------------------------------------------
def test_le_mot_de_passe_n_est_ni_dans_la_definition_ni_dans_l_environnement(host):
    """Trois affirmations qui ne font qu'une exigence : la valeur n'est lisible
    que là où le cahier des charges l'a mise.

    La première version de ce test ne regardait que le manifeste, et l'énoncé
    disait « n'apparaît dans aucun manifeste ». C'était attaquable : un
    candidat qui écrit son Secret en YAML avec `stringData` met bien la valeur
    dans un manifeste, tout en faisant exactement ce qu'on attend de lui. Ce
    qui compte n'est pas le fichier, c'est ce que porte le WORKLOAD, et ce que
    le conteneur expose à ses processus. L'énoncé le dit maintenant ainsi.
    """
    s = _json(host, f"-n {NAMESPACE} get secret {SECRET}", f"L'objet {SECRET}")
    assert "password" in (s.get("data") or {}), message(
        en=f"Object {SECRET} exists but has no password key. It carries "
        f"{sorted((s.get('data') or {}).keys()) or 'no key'}.",
        fr=f"L'objet {SECRET} existe mais n'a pas de clé password. Il porte "
        f"{sorted((s.get('data') or {}).keys()) or 'aucune clé'}.",
    )
    rc, manifeste, _ = _kubectl(host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT} -o yaml")
    assert rc == 0, message(
        en=f"Cannot read the definition of {DEPLOIEMENT} in {NAMESPACE}.",
        fr=f"Impossible de lire la définition de {DEPLOIEMENT} dans {NAMESPACE}.",
    )
    assert MOT_DE_PASSE not in manifeste, message(
        en="The password appears in clear text in the catalogue's definition. "
        "The dedicated object is useless as long as the value is also written "
        "next to it: the container must receive it from that object, not carry it.",
        fr="Le mot de passe apparaît en clair dans la définition du catalogue. "
        "L'objet dédié ne sert à rien tant que la valeur est aussi écrite à "
        "côté : le conteneur doit la recevoir de cet objet, pas la porter.",
    )
    # Le mot de passe ne doit pas non plus être posé dans l'environnement du
    # conteneur : `printenv` sans argument liste ce que voient TOUS ses
    # processus, et un fichier monté n'y figure pas.
    rc, environnement, _ = _dans_le_conteneur(host, "printenv")
    assert rc == 0, message(
        en="Cannot read the container's environment.",
        fr="Impossible de lire l'environnement du conteneur.",
    )
    assert MOT_DE_PASSE not in environnement, message(
        en="The password is placed in the container's environment. Every "
        "command run inside sees it, and it shows up in a `kubectl "
        "describe pod` as in most crash logs: the specification "
        "asks for a file, precisely to avoid that.",
        fr="Le mot de passe est posé dans l'environnement du conteneur. Toute "
        "commande lancée dedans le voit, et il ressort dans un `kubectl "
        "describe pod` comme dans la plupart des journaux de crash : le cahier "
        "des charges demande un fichier, précisément pour éviter cela.",
    )


def test_le_conteneur_lit_le_mot_de_passe_dans_un_fichier(host):
    """La preuve : le fichier existe, au bon endroit, avec la bonne valeur.

    Monter un Secret en variable d'environnement passerait le test précédent
    et échouerait ici, et c'est voulu : le cahier des charges nomme un
    fichier.
    """
    rc, sortie, diagnostic = _dans_le_conteneur(host, "cat /etc/db/password")
    assert rc == 0, message(
        en="File /etc/db/password does not exist in the container. The "
        "specification asks for the password to be readable there: an "
        f"environment variable does not satisfy that requirement. Output: {diagnostic}",
        fr="Le fichier /etc/db/password n'existe pas dans le conteneur. Le cahier "
        "des charges demande que le mot de passe s'y lise : une variable "
        f"d'environnement ne satisfait pas cette exigence. Sortie : {diagnostic}",
    )
    assert sortie == MOT_DE_PASSE, message(
        en=f"The file contains \"{sortie}\", expected \"{MOT_DE_PASSE}\".",
        fr=f"Le fichier contient « {sortie} », attendu « {MOT_DE_PASSE} ».",
    )


# ----------------------------------------------------------------------
# Exigence 4. Deux sondes, et elles ne font pas tomber le Pod.
# ----------------------------------------------------------------------
def test_les_deux_sondes_sont_declarees(host):
    """Une seule sonde ne répond qu'à la moitié de la question posée."""
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT}", f"Le Deployment {DEPLOIEMENT}")
    conteneurs = d["spec"]["template"]["spec"]["containers"]
    manquantes = [
        nom
        for nom in ("readinessProbe", "livenessProbe")
        if not any(c.get(nom) for c in conteneurs)
    ]
    assert not manquantes, message(
        en=f"Missing probe(s): {', '.join(manquantes)}. The specification "
        "asks for two distinct checks: one decides whether a replica receives "
        "traffic, the other whether it must be restarted.",
        fr=f"Sonde(s) absente(s) : {', '.join(manquantes)}. Le cahier des charges "
        "demande deux contrôles distincts : l'un décide si un exemplaire reçoit "
        "du trafic, l'autre s'il faut le redémarrer.",
    )


def test_les_sondes_ne_font_pas_redemarrer_les_exemplaires(host):
    """La preuve comportementale, et elle attrape le piège du port.

    Une sonde qui vise le port 80 alors que le conteneur écoute sur 8080 est
    syntaxiquement correcte, et tue le Pod en boucle. Le test précédent la
    laisserait passer ; celui-ci non.
    """
    rc, sortie, _ = _kubectl(
        host,
        f"-n {NAMESPACE} get pods -l {_selecteur(host)} "
        "-o jsonpath='{.items[*].status.containerStatuses[*].restartCount}'",
    )
    assert rc == 0, message(
        en="Cannot read the state of the catalogue's Pods.",
        fr="Impossible de lire l'état des Pods du catalogue.",
    )
    redemarrages = [int(n) for n in sortie.split()] if sortie else []
    assert redemarrages, message(
        en="No catalogue Pod has a readable container state: the delivery "
        "is not running.",
        fr="Aucun Pod du catalogue n'a d'état de conteneur lisible : la livraison "
        "ne tourne pas.",
    )
    assert max(redemarrages) == 0, message(
        en=f"One replica has already restarted {max(redemarrages)} times. A liveness "
        "probe that fails kills the container in a loop: check that it targets "
        "the port the container ACTUALLY listens on, and that it gives it "
        "time to start.",
        fr=f"Un exemplaire a déjà redémarré {max(redemarrages)} fois. Une sonde de "
        "vivacité qui échoue tue le conteneur en boucle : vérifiez qu'elle vise "
        "le port sur lequel le conteneur écoute RÉELLEMENT, et qu'elle lui "
        "laisse le temps de démarrer.",
    )


# ----------------------------------------------------------------------
# Exigence 5. Le manifeste impose l'identité, l'image ne suffit pas.
# ----------------------------------------------------------------------
def test_le_conteneur_ne_tourne_pas_en_root(host):
    """Deux affirmations, et la seconde est la vraie.

    L'image choisie tourne déjà en 101 sans qu'on lui demande rien : lire
    seulement `id -u` validerait un manifeste muet. On exige donc aussi que
    le manifeste le DISE, comme le cahier des charges le demande.
    """
    d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOIEMENT}", f"Le Deployment {DEPLOIEMENT}")
    gabarit = d["spec"]["template"]["spec"]
    declares = [(gabarit.get("securityContext") or {}).get("runAsUser")]
    declares += [
        (c.get("securityContext") or {}).get("runAsUser") for c in gabarit["containers"]
    ]
    assert int(UID_ATTENDU) in [v for v in declares if v is not None], message(
        en=f"The manifest does not declare runAsUser {UID_ATTENDU}. The image may "
        "already run as non-root, but the specification asks for the manifest "
        "to say so: a replaced image must not be able to put the delivery "
        "back as root with nothing else changing.",
        fr=f"Le manifeste ne déclare pas runAsUser {UID_ATTENDU}. L'image tourne "
        "peut-être déjà en non-root, mais le cahier des charges demande que ce "
        "soit le manifeste qui le dise : une image remplacée ne doit pas pouvoir "
        "faire repasser la livraison en root sans que rien ne change.",
    )
    rc, sortie, diagnostic = _dans_le_conteneur(host, "id -u")
    assert rc == 0, message(
        en=f"Cannot get into the container: {diagnostic}",
        fr=f"Impossible d'entrer dans le conteneur : {diagnostic}",
    )
    assert sortie == UID_ATTENDU, message(
        en=f"The process runs as {sortie}, expected {UID_ATTENDU}.",
        fr=f"Le processus tourne en {sortie}, attendu {UID_ATTENDU}.",
    )


# ----------------------------------------------------------------------
# Exigence 6, premier temps : le nom stable répond.
# ----------------------------------------------------------------------
def test_la_boutique_repond_au_nom_stable(host):
    """Depuis frontend, qui est censé avoir le droit d'entrer.

    Ce test éprouve du même coup le Service, sa traduction de port et la
    politique réseau du côté permis. S'il échoue alors que les Pods sont
    prêts, le selector ou le targetPort sont en cause, ou la politique bloque
    ce qu'elle devrait laisser passer.
    """
    svc = _json(host, f"-n {NAMESPACE} get service {SERVICE}", f"Le Service {SERVICE}")
    ports = [p.get("port") for p in svc["spec"].get("ports", [])]
    assert 80 in ports, message(
        en=f"Service {SERVICE} exposes port(s) {ports}. The specification "
        "asks for port 80 on the client side, whatever the container's "
        "port behind it.",
        fr=f"Le Service {SERVICE} présente le(s) port(s) {ports}. Le cahier des "
        "charges demande le port 80 côté client, quel que soit le port du "
        "conteneur derrière.",
    )
    passe, diagnostic = _joint_la_boutique(host, "frontend")
    assert passe, message(
        en=f"The frontend Pod does not reach http://{SERVICE}/ although it is "
        "allowed to. Three possible causes, in this order: the Service's selector "
        "does not designate the catalogue's Pods, its targetPort does not match "
        "the container's listening port, or the network policy also blocks what "
        f"it should allow. Output: {diagnostic}",
        fr=f"Le Pod frontend ne joint pas http://{SERVICE}/ alors qu'il en a le "
        "droit. Trois causes possibles, dans cet ordre : le selector du Service "
        "ne désigne pas les Pods du catalogue, son targetPort ne correspond pas "
        "au port d'écoute du conteneur, ou la politique réseau bloque aussi ce "
        f"qu'elle devrait autoriser. Sortie : {diagnostic}",
    )


# ----------------------------------------------------------------------
# Exigence 6, second temps : LE test qui prouve quelque chose.
# ----------------------------------------------------------------------
def test_seul_le_frontend_joint_la_boutique(host):
    """Les deux sens, dans le même test, et c'est délibéré.

    Sans politique du tout, `frontend` passe : le test précédent passerait
    donc avant le travail. Seule la paire prouve l'isolation, et elle
    n'admet pas de demi-mesure : une politique qui bloque tout le monde
    échoue ici aussi.
    """
    permis, _ = _joint_la_boutique(host, "frontend")
    refuse, _ = _joint_la_boutique(host, "intrus")
    assert permis, message(
        en="The frontend Pod, which carries role=frontend, does not reach the shop. "
        "A policy that allows nothing is not an isolation policy, "
        "it is an outage. Mind the port named in the rule: a network "
        "policy applies to the Pod, and the packet has already been translated by "
        "the Service when it arrives, so it is the CONTAINER's port that the rule "
        "must name.",
        fr="Le Pod frontend, qui porte role=frontend, ne joint pas la boutique. "
        "Une politique qui n'autorise rien n'est pas une politique d'isolation, "
        "c'est une coupure. Attention au port nommé dans la règle : une "
        "politique réseau s'applique au Pod, le paquet a déjà été traduit par "
        "le Service quand il arrive, c'est donc le port du CONTENEUR qu'elle "
        "doit nommer.",
    )
    assert not refuse, message(
        en="The intrus Pod, which does not carry role=frontend, reaches the shop "
        "anyway: nothing stops it. As long as no policy selects "
        "the catalogue's Pods, the whole namespace has access.",
        fr="Le Pod intrus, qui ne porte pas role=frontend, joint quand même la "
        "boutique : rien ne l'en empêche. Tant qu'aucune politique ne sélectionne "
        "les Pods du catalogue, tout le namespace y a accès.",
    )
