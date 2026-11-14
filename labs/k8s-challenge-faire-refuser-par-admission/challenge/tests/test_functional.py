"""test_functional.py : k8s-challenge-faire-refuser-par-admission

Le challenge du module Politiques d'admission. Ces tests lisent l'état du
CLUSTER, jamais les commandes tapées. Un test vérifie un seul état, dans
l'ordre de la fiche.

Ils reprennent les mesures attestées de quatre labs guidés :
cks-pod-security-admission (états 1 à 4), cks-secure-existing-pod (états 5
à 8), cks-validating-admission-policy et cks-image-pinned-digest (états 9 et
10). Les refus se lisent par de VRAIES soumissions : un dry-run côté serveur,
qui traverse toute la chaîne d'admission sans rien écrire, pour le standard ;
une création réelle, aussitôt retirée, pour la politique native.

Ce que le challenge ajoute : l'état 10 exige qu'une image par tag passe
toujours dans le namespace témoin recette. Une politique liée à tout le
cluster refuserait aussi là, et ce ne serait plus une règle mais une panne.

Les dix tests échouent sur l'état que pose le setup : vitrine sans standard et
sans Pod, caisse privilégié et seul, aucune politique d'admission.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
VITRINE = "vitrine"
PAIEMENT = "paiement"
PRODUCTION = "production"
TEMOIN = "recette"
PREFIXE = "pod-security.kubernetes.io"
MODES = ("enforce", "warn", "audit")
CONFORME = "catalogue"
REMPLACANT = "caisse-durcie"
ORIGINAL = "caisse"
IMAGE_TAG = "busybox:1.37"
IMAGE_DIGEST = "busybox@sha256:ab33eacc8251e3807b85bb6dba570e4698c3998eca6f0fc2ccb60575a563ea74"
#: Un conteneur qui ne voit que ses propres processus en compte une poignée ;
#: avec le namespace PID du nœud, il en voit plus de cent.
PLAFOND_PROCESSUS = 30
#: L'API server recharge ses politiques après notification : budget borné pour
#: ne pas recaler une correction juste.
BUDGET_S = 60

#: Refusé par le standard restricted pour plusieurs raisons à la fois.
POD_INTERDIT = """apiVersion: v1
kind: Pod
metadata:
  name: sonde-interdite
  namespace: vitrine
spec:
  hostPID: true
  containers:
    - name: outil
      image: busybox:1.37
      securityContext:
        runAsUser: 0
"""

#: Le même Pod, rendu conforme : sans lui, un namespace qui refuserait TOUT
#: passerait le test du refus.
POD_ACCEPTABLE = """apiVersion: v1
kind: Pod
metadata:
  name: sonde-conforme
  namespace: vitrine
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: outil
      image: busybox:1.37
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
"""


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS : le client
    SSH écrit un avertissement sur stderr."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _pod(host, namespace: str, nom: str) -> dict | None:
    rc, sortie, _ = _kubectl(host, f"-n {namespace} get pod {nom} -o json")
    return json.loads(sortie) if rc == 0 and sortie else None


def _soumettre_a_sec(host, manifeste: str) -> tuple[bool, str]:
    """Soumet un Pod à l'admission SANS rien créer, et rend (accepté, réponse)."""
    cree = host.run("mktemp /tmp/dsoxlab-sonde-admission.XXXXXX.yaml")
    assert cree.rc == 0 and cree.stdout.strip(), message(
        en="mktemp failed on the node.",
        fr="mktemp a échoué sur le nœud.",
    )
    chemin = cree.stdout.strip()
    depose = host.run(f"cat > {chemin} <<'MANIFESTE'\n{manifeste}MANIFESTE")
    assert depose.rc == 0, message(
        en="Cannot drop the probe manifest onto the node.",
        fr="Impossible de déposer le manifeste de sonde sur le nœud.",
    )
    rc, sortie, diagnostic = _kubectl(host, f"apply --dry-run=server -f {chemin}")
    host.run(f"rm -f {chemin}")
    return rc == 0, diagnostic or sortie


def _supprimer(host, namespace: str, pod: str) -> None:
    """Supprime une sonde et ATTEND sa disparition : la tentative suivante se
    heurterait sinon à un Pod en cours de suppression."""
    _kubectl(host, f"-n {namespace} delete pod {pod} --ignore-not-found --wait=true --timeout=90s")


def _creer(host, namespace: str, nom: str, image: str) -> tuple[int, str]:
    """Crée réellement un Pod sonde, rend (code, message), puis le retire."""
    _supprimer(host, namespace, nom)
    rc, sortie, diagnostic = _kubectl(
        host,
        f"-n {namespace} run {nom} --image={image} --restart=Never "
        "--command -- sh -c 'sleep 30'",
    )
    _supprimer(host, namespace, nom)
    return rc, diagnostic or sortie


# ----------------------------------------------------------------------
# 1. vitrine déclare le standard restricted dans les trois modes.
# ----------------------------------------------------------------------
def test_vitrine_declare_restricted_dans_les_trois_modes(host):
    rc, sortie, diagnostic = _kubectl(host, f"get namespace {VITRINE} -o json")
    assert rc == 0 and sortie, message(
        en=f"Namespace {VITRINE} no longer exists: setup had created it. {diagnostic}",
        fr=f"Le namespace {VITRINE} n'existe plus : le setup l'avait créé. {diagnostic}",
    )
    labels = (json.loads(sortie).get("metadata") or {}).get("labels") or {}
    manquants = [m for m in MODES if labels.get(f"{PREFIXE}/{m}") != "restricted"]
    assert not manquants, message(
        en=f"Mode(s) missing or at the wrong level on {VITRINE}: {', '.join(manquants)}. "
        "The three modes are independent: warn and audit have never blocked anyone.",
        fr=f"Mode(s) absent(s) ou au mauvais niveau sur {VITRINE} : {', '.join(manquants)}. "
        "Les trois modes sont indépendants : warn et audit n'ont jamais bloqué personne.",
    )


# ----------------------------------------------------------------------
# 2. Le Pod conforme tourne dans vitrine.
# ----------------------------------------------------------------------
def test_le_pod_catalogue_tourne_dans_vitrine(host):
    pod = _pod(host, VITRINE, CONFORME)
    assert pod, message(
        en=f"No Pod {CONFORME} in {VITRINE}. It must satisfy the restricted standard "
        "to be admitted.",
        fr=f"Aucun Pod {CONFORME} dans {VITRINE}. Il doit satisfaire le standard "
        "restricted pour être admis.",
    )
    phase = pod["status"].get("phase")
    assert phase == "Running", message(
        en=f"Pod {CONFORME} is {phase}. It was admitted but does not run: look at its "
        "events and its logs.",
        fr=f"Le Pod {CONFORME} est en {phase}. Il a été admis mais ne tourne pas : "
        "regardez ses events et ses logs.",
    )


# ----------------------------------------------------------------------
# 3. Le Pod conforme satisfait les quatre exigences du standard.
# ----------------------------------------------------------------------
def test_le_pod_catalogue_satisfait_les_quatre_exigences(host):
    """Lues dans le Pod ADMIS. L'identité vaut au niveau du Pod comme du
    conteneur ; l'escalade et les capabilities n'existent qu'au niveau du
    conteneur."""
    pod = _pod(host, VITRINE, CONFORME)
    assert pod, message(
        en=f"Pod {CONFORME} cannot be found in {VITRINE}.",
        fr=f"Le Pod {CONFORME} est introuvable dans {VITRINE}.",
    )
    spec = pod["spec"]
    ctx_pod = spec.get("securityContext") or {}
    ecarts = []
    for conteneur in spec.get("containers") or []:
        ctx = conteneur.get("securityContext") or {}
        nom = conteneur.get("name")
        if not (ctx_pod.get("runAsNonRoot") or ctx.get("runAsNonRoot")):
            ecarts.append(f"{nom} : runAsNonRoot n'est déclaré ni sur le Pod ni sur le conteneur")
        if ctx.get("allowPrivilegeEscalation") is not False:
            ecarts.append(f"{nom} : allowPrivilegeEscalation n'est pas à false")
        if "ALL" not in ((ctx.get("capabilities") or {}).get("drop") or []):
            ecarts.append(f"{nom} : les capabilities ne sont pas toutes retirées (drop: ALL)")
        seccomp = (ctx.get("seccompProfile") or ctx_pod.get("seccompProfile") or {}).get("type")
        if seccomp not in ("RuntimeDefault", "Localhost"):
            ecarts.append(f"{nom} : aucun profil seccomp n'est déclaré")
    assert not ecarts, message(
        en="Pod catalogue does not meet what the standard requires:\n  " + "\n  ".join(ecarts),
        fr="Le Pod catalogue ne satisfait pas ce que le standard exige :\n  " + "\n  ".join(ecarts),
    )


# ----------------------------------------------------------------------
# 4. L'admission refuse l'interdit et accepte le conforme.
# ----------------------------------------------------------------------
def test_l_admission_refuse_l_interdit_et_accepte_le_conforme(host):
    """Les deux sens dans le même test : sans standard tout passe, avec un
    standard mal réglé tout peut être refusé. Seule la paire dit que
    l'admission trie. Rien n'est créé."""
    accepte, reponse = _soumettre_a_sec(host, POD_INTERDIT)
    assert not accepte, message(
        en=f"The API server ACCEPTED in {VITRINE} a Pod that shares the host's PID "
        "namespace and runs as root: the enforce mode does not target restricted.",
        fr=f"L'API server a ACCEPTÉ dans {VITRINE} un Pod qui partage le namespace PID "
        "de l'hôte et tourne en root : le mode enforce ne vise pas restricted.",
    )
    assert "PodSecurity" in reponse or "violate" in reponse, message(
        en=f"The Pod was refused, but not by Pod Security Admission: \"{reponse}\".",
        fr=f"Le Pod a été refusé, mais pas par Pod Security Admission : « {reponse} ».",
    )
    accepte, reponse = _soumettre_a_sec(host, POD_ACCEPTABLE)
    assert accepte, message(
        en=f"A Pod that satisfies the restricted standard is refused too: \"{reponse}\". "
        "An admission that refuses everything is an outage, not a policy.",
        fr=f"Un Pod qui satisfait le standard restricted est refusé lui aussi : "
        f"« {reponse} ». Une admission qui refuse tout est une panne, pas une politique.",
    )


# ----------------------------------------------------------------------
# 5. Le Pod de remplacement tourne.
# ----------------------------------------------------------------------
def test_le_pod_de_remplacement_tourne(host):
    pod = _pod(host, PAIEMENT, REMPLACANT)
    assert pod, message(
        en=f"No Pod {REMPLACANT} in {PAIEMENT}. The specification asks for {ORIGINAL} "
        "to be rebuilt under that name.",
        fr=f"Aucun Pod {REMPLACANT} dans {PAIEMENT}. Le cahier des charges demande de "
        f"reconstruire {ORIGINAL} sous ce nom.",
    )
    phase = pod["status"].get("phase")
    assert phase == "Running", message(
        en=f"Pod {REMPLACANT} is {phase}. A hardening that stops the container from "
        "starting fixes nothing: look at its events.",
        fr=f"Le Pod {REMPLACANT} est en {phase}. Un durcissement qui empêche le "
        "conteneur de démarrer ne corrige rien : regardez ses events.",
    )


# ----------------------------------------------------------------------
# 6. Le nouveau Pod ne conserve aucun des défauts de l'original.
# ----------------------------------------------------------------------
def test_le_pod_de_remplacement_ne_garde_aucun_defaut(host):
    pod = _pod(host, PAIEMENT, REMPLACANT)
    assert pod, message(
        en=f"No Pod {REMPLACANT} in {PAIEMENT}.",
        fr=f"Aucun Pod {REMPLACANT} dans {PAIEMENT}.",
    )
    spec = pod["spec"]
    ctx_pod = spec.get("securityContext") or {}
    restants = []
    if spec.get("hostPID"):
        restants.append("le Pod partage encore le namespace de processus de l'hôte (hostPID)")
    if spec.get("hostNetwork") or spec.get("hostIPC"):
        restants.append("le Pod partage un autre namespace de l'hôte (hostNetwork ou hostIPC)")
    for conteneur in spec.get("containers") or []:
        ctx = conteneur.get("securityContext") or {}
        nom = conteneur.get("name")
        if ctx.get("privileged"):
            restants.append(f"{nom} : le conteneur est encore privilégié")
        if ctx.get("allowPrivilegeEscalation") is not False:
            restants.append(f"{nom} : allowPrivilegeEscalation n'est pas explicitement à false")
        identites = [ctx_pod.get("runAsUser"), ctx.get("runAsUser")]
        if 0 in identites or not any(i for i in identites if i):
            restants.append(f"{nom} : tourne encore en root, ou n'impose aucun utilisateur")
        if "ALL" not in ((ctx.get("capabilities") or {}).get("drop") or []):
            restants.append(f"{nom} : les capacités du noyau ne sont pas toutes retirées (drop: ALL)")
        image = conteneur.get("image", "")
        if "@sha256:" not in image and (image.endswith(":latest") or ":" not in image.rsplit("/", 1)[-1]):
            restants.append(f"{nom} : l'image « {image} » emploie un tag flottant")
    assert not restants, message(
        en="The rebuilt Pod keeps some of the original's flaws:\n  " + "\n  ".join(restants),
        fr="Le Pod reconstruit garde des défauts de l'original :\n  " + "\n  ".join(restants),
    )


# ----------------------------------------------------------------------
# 7. Le Pod privilégié d'origine n'existe plus.
# ----------------------------------------------------------------------
def test_le_pod_privilegie_d_origine_n_existe_plus(host):
    rc, _, _ = _kubectl(host, f"-n {PAIEMENT} get pod {ORIGINAL}")
    assert rc != 0, message(
        en=f"Pod {ORIGINAL} still runs in {PAIEMENT}. The new Pod replaces nothing as "
        "long as the old one is there: it doubles the surface instead of reducing it.",
        fr=f"Le Pod {ORIGINAL} tourne toujours dans {PAIEMENT}. Le nouveau Pod ne "
        "remplace rien tant que l'ancien est là : il double la surface au lieu de la réduire.",
    )


# ----------------------------------------------------------------------
# 8. Le conteneur du nouveau Pod ne voit plus les processus de l'hôte.
# ----------------------------------------------------------------------
def test_le_conteneur_ne_voit_plus_les_processus_de_l_hote(host):
    """La preuve prise DANS le conteneur : `hostPID: false` n'est qu'une
    absence, ce qui se mesure est ce que le conteneur énumère."""
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {PAIEMENT} exec {REMPLACANT} --request-timeout=30s -- sh -c 'ps -eo pid | wc -l'"
    )
    assert rc == 0 and sortie.isdigit(), message(
        en=f"Cannot count the processes in {REMPLACANT}. Output: {diagnostic}",
        fr=f"Impossible de compter les processus dans {REMPLACANT}. Sortie : {diagnostic}",
    )
    vus = int(sortie)
    assert vus <= PLAFOND_PROCESSUS, message(
        en=f"The container sees {vus} processes: those of the NODE, kubelet and "
        "containerd included, to which it can send signals.",
        fr=f"Le conteneur voit {vus} processus : ceux du NŒUD, kubelet et containerd "
        "compris, auxquels il peut envoyer des signaux.",
    )
    rc, identite, _ = _kubectl(host, f"-n {PAIEMENT} exec {REMPLACANT} --request-timeout=30s -- id -u")
    assert rc == 0 and identite.isdigit() and identite != "0", message(
        en=f"The container's process runs as uid {identite or 'unknown'}. A root "
        "container that escapes is root on the node.",
        fr=f"Le processus du conteneur tourne en uid {identite or 'inconnu'}. Un "
        "conteneur root qui s'échappe est root sur le nœud.",
    )


# ----------------------------------------------------------------------
# 9. Une politique native est liée en mode refus.
# ----------------------------------------------------------------------
def _politiques(host) -> list[str]:
    rc, sortie, diagnostic = _kubectl(host, "get validatingadmissionpolicy -o json")
    assert rc == 0, message(
        en=f"Cannot read the admission policies. {diagnostic}",
        fr=f"Impossible de lire les politiques d'admission. {diagnostic}",
    )
    return [
        p["metadata"]["name"]
        for p in json.loads(sortie or "{}").get("items", [])
        if not p["metadata"]["name"].startswith("safe-upgrades")
    ]


def test_une_politique_native_est_liee_en_mode_refus(host):
    politiques = _politiques(host)
    assert politiques, message(
        en="No native admission policy in the cluster, the kind the API server "
        "evaluates itself, with no webhook to keep alive.",
        fr="Aucune politique d'admission native dans le cluster, celle que l'API "
        "server évalue lui-même, sans webhook à maintenir en vie.",
    )
    rc, sortie, diagnostic = _kubectl(host, "get validatingadmissionpolicybinding -o json")
    assert rc == 0, message(
        en=f"Cannot read the bindings. {diagnostic}",
        fr=f"Impossible de lire les liaisons. {diagnostic}",
    )
    liaisons = [
        b for b in json.loads(sortie or "{}").get("items", [])
        if b["spec"].get("policyName") in politiques
    ]
    assert liaisons, message(
        en=f"Policy or policies {politiques} are bound to nothing: a policy without a "
        "binding acts on no request.",
        fr=f"La ou les politiques {politiques} ne sont liées à rien : une politique "
        "sans liaison n'agit sur aucune requête.",
    )
    actions = {b["metadata"]["name"]: b["spec"].get("validationActions") for b in liaisons}
    assert any("Deny" in (b["spec"].get("validationActions") or []) for b in liaisons), message(
        en=f"No binding refuses: {actions}. Warn and Audit both LET THROUGH; only Deny refuses.",
        fr=f"Aucune liaison ne refuse : {actions}. Warn et Audit LAISSENT PASSER tous "
        "les deux ; seul Deny refuse.",
    )


# ----------------------------------------------------------------------
# 10. Tag refusé, digest accepté, autres namespaces non touchés.
# ----------------------------------------------------------------------
def test_le_tag_est_refuse_le_digest_passe_et_les_autres_namespaces_non_touches(host):
    """Preuve ACTIVE, dans les trois sens. « Le digest passe » et « le témoin
    accepte » sont vrais avant le travail : ils ne prennent leur sens qu'accolés
    au refus du tag."""
    fin = time.monotonic() + BUDGET_S
    rc_tag, refus = 0, ""
    while time.monotonic() < fin:
        rc_tag, refus = _creer(host, PRODUCTION, "sonde-tag", IMAGE_TAG)
        if rc_tag != 0:
            break
        time.sleep(3)
    assert rc_tag != 0, message(
        en=f"After {BUDGET_S} seconds, {PRODUCTION} still accepts \"{IMAGE_TAG}\", which "
        "is not pinned. Check that the binding does name this namespace.",
        fr=f"Après {BUDGET_S} secondes, {PRODUCTION} accepte toujours « {IMAGE_TAG} », "
        "qui n'est pas épinglée. Vérifiez que la liaison désigne bien ce namespace.",
    )
    assert "denied request" in refus.lower() or "validatingadmissionpolicy" in refus.lower(), message(
        en=f"The Pod was refused, but not by an admission policy. The message was: {refus}",
        fr=f"Le Pod a été refusé, mais pas par une politique d'admission. Le message était : {refus}",
    )

    rc, reponse = _creer(host, PRODUCTION, "sonde-digest", IMAGE_DIGEST)
    assert rc == 0, message(
        en=f"The pinned image is refused too in {PRODUCTION}: {reponse}. The policy "
        "must tell a pinned image from a tag, not block the namespace.",
        fr=f"L'image épinglée est refusée elle aussi dans {PRODUCTION} : {reponse}. La "
        "politique doit distinguer une image épinglée d'un tag, pas bloquer le namespace.",
    )
    pod = _pod(host, PRODUCTION, "conforme")
    assert pod and pod["status"].get("phase") == "Running", message(
        en="The pinned Pod conforme, placed by setup, no longer runs. A policy only "
        "judges at creation: it was deleted, not refused.",
        fr="Le Pod épinglé conforme, posé par le setup, ne tourne plus. Une politique "
        "ne juge qu'à la création : il a été supprimé, pas refusé.",
    )

    rc, reponse = _creer(host, TEMOIN, "sonde-temoin", IMAGE_TAG)
    assert rc == 0, message(
        en=f"An image by tag is refused in {TEMOIN} as well: {reponse}. The rule asked "
        f"for applies to {PRODUCTION} only; bound to the whole cluster, it also blocks "
        "the system namespaces, whose images are not pinned.",
        fr=f"Une image par tag est refusée aussi dans {TEMOIN} : {reponse}. La règle "
        f"demandée ne vaut que pour {PRODUCTION} ; liée à tout le cluster, elle bloque "
        "aussi les namespaces système, dont les images ne sont pas épinglées.",
    )
