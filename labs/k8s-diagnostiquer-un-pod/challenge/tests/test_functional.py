"""test_functional.py : k8s-diagnostiquer-un-pod

Ces tests confrontent le relevé ~/pods-en-panne/releve.txt à l'état réel des
deux Pods, puis vérifient que chaque Pod a été réparé du geste juste. Un test
vérifie un seul état demandé par l'énoncé.

L'image d'un Pod se corrige en place : image-fausse doit garder l'uid que le
setup a mémorisé, un Pod recréé ne compte pas. La commande, elle, ne se modifie
pas sur un Pod existant : plante doit être recréé, et on vérifie qu'il porte le
même nom, la même image, et qu'il tourne sans redémarrer.

Aucun test n'attend tant que le travail n'est pas commencé : une attente ne
s'ouvre que si la correction est déjà posée et que le Pod démarre encore.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "pods-en-panne"
MEMOIRE = "/var/lib/dsoxlab/diagnostiquer-un-pod.json"
RELEVE = f"~/{NS}/releve.txt"
IMAGE_CORRIGEE = "nginx:1.30.5"
IMAGE_PLANTE = "busybox:1.38.0"
#: Durée minimale pendant laquelle plante doit avoir tourné d'une traite : un
#: conteneur qui sort en erreur est redémarré en quelques secondes.
STABLE = 15
ATTENTE = 60
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    assert res.rc == 0, message(
        en="The memory of the initial state is missing: run dsoxlab reset k8s-diagnostiquer-un-pod.",
        fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-diagnostiquer-un-pod.",
    )
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def releve(host) -> dict[str, str]:
    fichier = host.file(f"{_maison(host)}/{NS}/releve.txt")
    if not fichier.exists:
        return {}
    valeurs: dict[str, str] = {}
    for brute in fichier.content_string.splitlines():
        ligne = brute.strip()
        if ligne and not ligne.startswith("#") and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            valeurs[cle.strip().lower()] = valeur.strip()
    return valeurs


def _valeur(releve: dict[str, str], cle: str) -> str:
    valeur = releve.get(cle, "")
    assert valeur, message(
        en=f"The key {cle!r} of {RELEVE} has no value.",
        fr=f"La clé {cle!r} de {RELEVE} n'a pas de valeur.",
    )
    return valeur


def _compact(texte: str) -> str:
    """Sans accents, sans casse, sans espaces ni ponctuation : « Image Pull
    Back-Off » et « imagepullbackoff » se comparent pareil."""
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if c.isalnum())


def _image(reference: str) -> str:
    """La référence sans digest ni préfixe du registre par défaut :
    ``docker.io/library/nginx:1.30.5@sha256:...`` vaut ``nginx:1.30.5``."""
    sans = reference.split("@", 1)[0]
    for prefixe in ("docker.io/library/", "index.docker.io/library/"):
        if sans.startswith(prefixe):
            return sans[len(prefixe):]
    return sans


def _pod(host, nom: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} get pod {nom} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _etat(pod: dict) -> dict:
    return ((pod.get("status") or {}).get("containerStatuses") or [{}])[0]


# ----------------------------------------------------------------------
# 1. La raison d'attente de image-fausse.
# ----------------------------------------------------------------------
def test_la_raison_d_attente_de_image_fausse_est_consignee(releve):
    valeur = _valeur(releve, "raison-image-fausse")
    lue = _compact(valeur)
    assert "errimagepull" in lue or "imagepullbackoff" in lue, message(
        en=f"raison-image-fausse is {valeur!r}. The waiting reason of an image that cannot be "
        "pulled alternates between two values, read in the STATUS column or in the Reason of "
        "kubectl describe pod. Reread the section of the lesson on an image that cannot be found.",
        fr=f"raison-image-fausse vaut {valeur!r}. La raison d'attente d'une image introuvable "
        "alterne entre deux valeurs, lues dans la colonne STATUS ou dans le Reason de "
        "kubectl describe pod. Relisez la section de la leçon sur l'image introuvable.",
    )


# ----------------------------------------------------------------------
# 2. Le code de sortie du conteneur de plante.
# ----------------------------------------------------------------------
def test_le_code_de_sortie_de_plante_est_consigne(releve):
    valeur = _valeur(releve, "code-sortie-plante")
    nombres = set(re.findall(r"\d+", valeur))
    assert nombres == {"1"}, message(
        en=f"code-sortie-plante is {valeur!r}. The exit code of the last stopped container is "
        "in lastState.terminated.exitCode, or in the Last State of kubectl describe pod. "
        "Reread the section of the lesson on a container that crashes.",
        fr=f"code-sortie-plante vaut {valeur!r}. Le code de sortie du dernier conteneur arrêté "
        "se lit dans lastState.terminated.exitCode, ou dans le Last State de "
        "kubectl describe pod. Relisez la section de la leçon sur le conteneur qui plante.",
    )


# ----------------------------------------------------------------------
# 3. image-fausse réparée en place.
# ----------------------------------------------------------------------
def test_image_fausse_tourne_avec_son_image_corrigee_en_place(host, memoire):
    pod = _pod(host, "image-fausse")
    assert pod is not None, message(
        en=f"No Pod image-fausse in {NS}: it was deleted. The image of a Pod is corrected in "
        "place, without deleting it. Run dsoxlab reset k8s-diagnostiquer-un-pod to start over.",
        fr=f"Aucun Pod image-fausse dans {NS} : il a été supprimé. L'image d'un Pod se corrige "
        "en place, sans le supprimer. Lancez dsoxlab reset k8s-diagnostiquer-un-pod pour repartir.",
    )
    assert pod["metadata"]["uid"] == memoire["image-fausse"], message(
        en="image-fausse is a new Pod, recreated under the same name. A container's image is one "
        "of the few fields Kubernetes allows to change on an existing Pod. In this lab, fix it "
        "without deleting the Pod. Run dsoxlab reset k8s-diagnostiquer-un-pod to start over.",
        fr="image-fausse est un nouveau Pod, recréé sous le même nom. L'image d'un conteneur fait "
        "partie des rares champs que Kubernetes autorise à modifier sur un Pod existant. Dans ce "
        "lab, corrigez-la sans supprimer le Pod. Lancez dsoxlab reset k8s-diagnostiquer-un-pod "
        "pour repartir.",
    )
    image = _image(pod["spec"]["containers"][0].get("image", ""))
    assert image == IMAGE_CORRIGEE, message(
        en=f"image-fausse asks for {image!r}, expected {IMAGE_CORRIGEE!r}.",
        fr=f"image-fausse demande {image!r}, attendu {IMAGE_CORRIGEE!r}.",
    )
    # L'image est la bonne : on laisse au kubelet le temps de la télécharger.
    fin = time.monotonic() + ATTENTE
    while not _etat(pod).get("ready") and time.monotonic() < fin:
        time.sleep(PAS)
        pod = _pod(host, "image-fausse") or pod
    assert _etat(pod).get("ready"), message(
        en=f"image-fausse asks for the right image but is not ready after {ATTENTE}s: "
        "kubectl describe pod image-fausse says why, in its Events.",
        fr=f"image-fausse demande la bonne image mais n'est pas prêt après {ATTENTE}s : "
        "kubectl describe pod image-fausse dit pourquoi, dans ses Events.",
    )


# ----------------------------------------------------------------------
# 4. plante recréé avec une commande qui ne sort pas.
# ----------------------------------------------------------------------
def test_plante_tourne_avec_sa_commande_corrigee(host):
    pod = _pod(host, "plante")
    assert pod is not None, message(
        en=f"No Pod plante in {NS}. Its command cannot change on an existing Pod: it is "
        "recreated under the SAME name, from its corrected manifest.",
        fr=f"Aucun Pod plante dans {NS}. Sa commande ne change pas sur un Pod existant : il "
        "se recrée sous le MÊME nom, depuis son manifeste corrigé.",
    )
    image = _image(pod["spec"]["containers"][0].get("image", ""))
    assert image == IMAGE_PLANTE, message(
        en=f"plante runs {image!r}, whereas its image {IMAGE_PLANTE!r} was not the problem: "
        "only its command was. Keep the image, correct the command.",
        fr=f"plante tourne avec {image!r}, alors que son image {IMAGE_PLANTE!r} n'était pas en "
        "cause : seule sa commande l'était. Gardez l'image, corrigez la commande.",
    )
    etat = _etat(pod)
    assert etat.get("restartCount", 0) == 0, message(
        en=f"plante's container has restarted {etat.get('restartCount')} time(s): its command "
        "still ends. A Pod is not modified in place for that: recreate it, under the same name, "
        "with a command that keeps running.",
        fr=f"Le conteneur de plante a redémarré {etat.get('restartCount')} fois : sa commande "
        "se termine encore. Un Pod ne se modifie pas en place pour cela : recréez-le, sous le "
        "même nom, avec une commande qui dure.",
    )
    en_marche = (etat.get("state") or {}).get("running")
    assert en_marche, message(
        en=f"plante's container is not running: {etat.get('state')}.",
        fr=f"Le conteneur de plante ne tourne pas : {etat.get('state')}.",
    )
    # Il tourne et n'a jamais redémarré : on vérifie qu'il TIENT, sans plus.
    fin = time.monotonic() + STABLE + 5
    while time.monotonic() < fin:
        pod = _pod(host, "plante") or pod
        etat = _etat(pod)
        if etat.get("restartCount", 0) or not (etat.get("state") or {}).get("running"):
            break
        debut = (etat["state"]["running"].get("startedAt") or "")
        ecoule = host.run(f"echo $(( $(date +%s) - $(date -d '{debut}' +%s) ))")
        if ecoule.rc == 0 and int(ecoule.stdout.strip() or 0) >= STABLE:
            break
        time.sleep(PAS)
    assert etat.get("restartCount", 0) == 0 and (etat.get("state") or {}).get("running"), message(
        en=f"plante's container stopped again within {STABLE}s: its command still ends.",
        fr=f"Le conteneur de plante s'est de nouveau arrêté en moins de {STABLE}s : sa commande "
        "se termine encore.",
    )
