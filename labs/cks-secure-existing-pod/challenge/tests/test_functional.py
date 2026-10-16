"""test_functional.py : cks-secure-existing-pod

Quatre affirmations qui lisent l'état du CLUSTER et l'intérieur du conteneur,
jamais les commandes tapées.

La dernière est la seule qui prouve quelque chose. Lire `hostPID: false` dans
une spec ne montre qu'une absence ; ce qui se mesure, c'est ce que le conteneur
VOIT. Avec le namespace de processus de l'hôte, il énumère tout ce qui tourne
sur la machine, kubelet et containerd compris, et peut leur envoyer des
signaux. Sans lui, il ne voit que les siens, et la différence se compte.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "production"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
POD = "secure-app"
FAUTIF = "insecure-app"
#: Un conteneur qui ne voit que ses propres processus en compte une poignée.
#: Le nœud, lui, en fait tourner plus de cent. Le seuil est large à dessein :
#: on mesure un ordre de grandeur, pas un nombre exact, qui varierait.
PLAFOND_PROCESSUS = 30


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    """Rend (code, sortie standard, diagnostic), les trois SÉPARÉS."""
    res = host.run(f"sudo {KUBECTL} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _pod(host) -> dict:
    rc, sortie, diagnostic = _kubectl(host, f"-n {NAMESPACE} get pod {POD} -o json")
    assert rc == 0 and sortie, message(
        en=f"No Pod {POD} in {NAMESPACE}. The specification asks for "
        f"{FAUTIF} to be rebuilt under that name. Output: {diagnostic}",
        fr=f"Aucun Pod {POD} dans {NAMESPACE}. Le cahier des charges demande de "
        f"reconstruire {FAUTIF} sous ce nom. Sortie : {diagnostic}",
    )
    return json.loads(sortie)


# ----------------------------------------------------------------------
# 1. Le Pod corrigé existe et tourne.
# ----------------------------------------------------------------------
def test_le_pod_corrige_tourne(host):
    pod = _pod(host)
    assert pod["status"]["phase"] == "Running", message(
        en=f"Pod {POD} is {pod['status']['phase']}. A hardening that "
        "stops the container from starting fixes nothing: look at its events "
        "and its logs. The busybox image runs without difficulty as a non-root "
        "user, it writes nothing at the root.",
        fr=f"Le Pod {POD} est en {pod['status']['phase']}. Un durcissement qui "
        "empêche le conteneur de démarrer ne corrige rien : regardez ses events "
        "et ses logs. L'image busybox tourne sans difficulté en utilisateur non "
        "root, elle n'écrit rien à la racine.",
    )


# ----------------------------------------------------------------------
# 2. Les cinq défauts sont repris, aucun n'est resté.
# ----------------------------------------------------------------------
def test_les_cinq_defauts_sont_repris(host):
    """On les vérifie ensemble : corriger quatre défauts sur cinq laisse le
    Pod exploitable, et un rapport de remédiation partielle est pire qu'un
    rapport d'absence de remédiation, parce qu'il rassure."""
    pod = _pod(host)
    spec = pod["spec"]
    conteneur = spec["containers"][0]
    ctx_pod = spec.get("securityContext") or {}
    ctx_ctn = conteneur.get("securityContext") or {}

    restants = []
    if spec.get("hostPID"):
        restants.append("le Pod partage encore le namespace de processus de l'hôte (hostPID)")
    if spec.get("hostNetwork") or spec.get("hostIPC"):
        restants.append("le Pod partage encore un autre namespace de l'hôte (hostNetwork ou hostIPC)")
    if ctx_ctn.get("privileged"):
        restants.append("le conteneur est encore privilégié")
    if ctx_ctn.get("allowPrivilegeEscalation") is not False:
        restants.append("allowPrivilegeEscalation n'est pas explicitement à false")
    identites = [ctx_pod.get("runAsUser"), ctx_ctn.get("runAsUser")]
    if 0 in identites or not any(i for i in identites if i):
        restants.append("le conteneur tourne encore en root, ou n'impose aucun utilisateur")
    if "ALL" not in ((ctx_ctn.get("capabilities") or {}).get("drop") or []):
        restants.append("les capacités du noyau ne sont pas toutes retirées (drop: ALL)")
    image = conteneur.get("image", "")
    if image.endswith(":latest") or ":" not in image.rsplit("/", 1)[-1]:
        restants.append(f"l'image « {image} » emploie un tag flottant")

    assert not restants, message(
        en="The rebuilt Pod keeps some of the original's flaws:\n  "
        + "\n  ".join(restants),
        fr="Le Pod reconstruit garde des défauts de l'original :\n  "
        + "\n  ".join(restants),
    )


# ----------------------------------------------------------------------
# 3. Le Pod fautif a disparu.
# ----------------------------------------------------------------------
def test_le_pod_fautif_n_existe_plus(host):
    """Corriger sans retirer l'original laisse la faille ouverte à côté du
    correctif. C'est le défaut le plus fréquent d'une remédiation faite dans
    l'urgence, et le seul que l'auteur ne voit jamais."""
    rc, _, _ = _kubectl(host, f"-n {NAMESPACE} get pod {FAUTIF}")
    assert rc != 0, message(
        en=f"Pod {FAUTIF} is still running in {NAMESPACE}. The new Pod replaces "
        "nothing as long as the old one is there: it doubles the surface instead "
        "of reducing it.",
        fr=f"Le Pod {FAUTIF} tourne toujours dans {NAMESPACE}. Le nouveau Pod ne "
        "remplace rien tant que l'ancien est là : il double la surface au lieu "
        "de la réduire.",
    )


# ----------------------------------------------------------------------
# 4. LE test : le conteneur ne voit plus l'hôte.
# ----------------------------------------------------------------------
def test_le_conteneur_ne_voit_plus_les_processus_de_l_hote(host):
    """La preuve, prise DANS le conteneur, et elle se compte.

    `hostPID: false` dans une spec n'est qu'une absence. Ce qui se mesure est
    ce que le conteneur énumère : avec le namespace de l'hôte il voit le
    kubelet, containerd et tous les autres conteneurs du nœud, plus de cent
    processus ; sans lui, une poignée.
    """
    rc, sortie, diagnostic = _kubectl(
        host, f"-n {NAMESPACE} exec {POD} --request-timeout=30s -- sh -c 'ps -eo pid | wc -l'"
    )
    assert rc == 0 and sortie.isdigit(), message(
        en=f"Cannot count the processes in {POD}. Output: {diagnostic}",
        fr=f"Impossible de compter les processus dans {POD}. Sortie : {diagnostic}",
    )
    vus = int(sortie)
    assert vus <= PLAFOND_PROCESSUS, message(
        en=f"The container sees {vus} processes. It therefore sees the NODE's: the "
        "kubelet, containerd, and every other container on the machine, "
        "to which it can send signals. That is what hostPID grants, and "
        "that is what the remediation had to remove.",
        fr=f"Le conteneur voit {vus} processus. Il voit donc ceux du NŒUD : le "
        "kubelet, containerd, et tous les autres conteneurs de la machine, "
        "auxquels il peut envoyer des signaux. C'est ce que hostPID accorde, et "
        "c'est ce que la remédiation devait retirer.",
    )

    rc, identite, _ = _kubectl(
        host, f"-n {NAMESPACE} exec {POD} --request-timeout=30s -- id -u"
    )
    assert rc == 0 and identite != "0", message(
        en=f"The container's process runs as uid {identite}. A root container "
        "that escapes is root on the node.",
        fr=f"Le processus du conteneur tourne en uid {identite}. Un conteneur root "
        "qui s'échappe est root sur le nœud.",
    )
