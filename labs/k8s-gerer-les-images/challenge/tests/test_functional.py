"""test_functional.py : k8s-gerer-les-images

Ces tests lisent dans le cluster « lab » l'image d'affiche et le digest que ses
Pods font tourner, comparé à celui que le setup a mémorisé ; le relevé
~/galerie/releve.txt et sa date, comparée à la création du Pod de vignettes qui
tourne ; puis d'où vient le Secret de pull de vignettes. Un test vérifie un
seul état demandé par l'énoncé.

Depuis le 2026-11-20, le ServiceAccount de vignettes porte DÉJÀ un Secret de
pull, posé par la préparation avec un mot de passe faux : le registre répond
401 Unauthorized (mesuré sur kind, registry 3.1.2). La cause attendue n'est
plus le « no basic auth credentials » que la leçon imprime, et les mots
génériques (secret, identifiant) ne suffisent plus. La réparation corrige un
Secret qui existe : sa date de création ne dit plus rien. Ce n'est pas non
plus la naissance des Pods, puisqu'un Pod existant démarre seul une fois le
Secret corrigé (le kubelet le relit à chaque tentative de pull, relevé par
le blog le 2026-11-20). C'est la dernière écriture du ServiceAccount et de
ses Secrets de pull qui la marque.

Tous échouent avant le travail : affiche tourne sur un tag, le relevé n'existe
pas, et vignettes est en ImagePullBackOff.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "galerie"
MEMOIRE = "/var/lib/dsoxlab/gerer-les-images.json"
REGISTRE = "localhost:30500"
#: Ce qui dit la cause d'un pull refusé pour un mauvais mot de passe : le code
#: et le mot que le registre renvoie, lus dans les événements du Pod.
CAUSE = re.compile(r"401|unauthori[sz]ed", re.IGNORECASE)
#: La requête que le registre refuse, telle que l'événement la donne (mesuré
#: le 2026-11-20 : « HEAD request to http://localhost:30500/v2/galerie/
#: vignettes/manifests/1.0: 401 Unauthorized »). Le code seul se devine ; le
#: chemin de la requête ne se lit que dans l'événement.
REQUETE = re.compile(r"/v2/galerie/vignettes/manifests/1\.0")
ATTENTE = 90
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset k8s-gerer-les-images.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-gerer-les-images.",
        ))
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _pods(host, app: str) -> list[dict]:
    return [p for p in (_json(host, f"-n {NS} get pods -l app={app}") or {}).get("items", [])
            if not p["metadata"].get("deletionTimestamp")]


def _derniere_ecriture(objet: dict) -> float | None:
    """La date de la dernière écriture d'un objet, lue dans ses managedFields."""
    dates = [m.get("time") for m in (objet.get("metadata") or {}).get("managedFields") or [] if m.get("time")]
    if not dates:
        return None
    return max(datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp() for d in dates)


def _derniere_ecriture_des_identifiants(host) -> float | None:
    """La dernière écriture du ServiceAccount vignettes et de ses Secrets de pull."""
    sa = _json(host, f"-n {NS} get serviceaccount vignettes") or {}
    objets = [sa] + [_json(host, f"-n {NS} get secret {s.get('name')}") or {}
                     for s in sa.get("imagePullSecrets") or []]
    dates = [d for d in (_derniere_ecriture(o) for o in objets if o) if d is not None]
    return max(dates) if dates else None


def _disponible(d: dict) -> bool:
    s = d.get("status") or {}
    voulus = d["spec"].get("replicas", 1)
    return s.get("observedGeneration") == d["metadata"]["generation"] \
        and s.get("updatedReplicas") == voulus and s.get("availableReplicas") == voulus


def _attendre_deploiement(host, nom: str) -> dict | None:
    d = _json(host, f"-n {NS} get deployment {nom}")
    fin = time.monotonic() + ATTENTE
    while d is not None and not _disponible(d) and time.monotonic() < fin:
        time.sleep(PAS)
        d = _json(host, f"-n {NS} get deployment {nom}") or d
    return d


# ----------------------------------------------------------------------
# 1. affiche est figée par le digest qu'elle faisait tourner.
# ----------------------------------------------------------------------
def test_affiche_est_figee_par_le_digest_qu_elle_faisait_tourner(host, memoire):
    attendu = memoire["affiche_digest"]
    d = _json(host, f"-n {NS} get deployment affiche")
    assert d is not None, message(
        en="The affiche Deployment no longer exists.",
        fr="Le Deployment affiche n'existe plus.",
    )
    image = d["spec"]["template"]["spec"]["containers"][0].get("image", "")
    if "@" in image:
        d = _attendre_deploiement(host, "affiche") or d
    digest = image.split("@", 1)[1] if "@" in image else None
    lancees = sorted({(c.get("imageID") or "").split("@")[-1]
                      for p in _pods(host, "affiche") for c in (p.get("status") or {}).get("containerStatuses") or []})
    assert digest == attendu and lancees == [attendu] and _disponible(d), message(
        en=f"affiche refers to {image!r} and its Pods run {lancees}. Expected: the image pinned by the "
        "digest of the very image it was running on its tag, every Pod on that digest, all available. "
        "Another digest, even of a close version, is another image.",
        fr=f"affiche désigne {image!r} et ses Pods tournent sur {lancees}. Attendu : l'image figée par "
        "le digest de l'image même qu'elle faisait tourner sur son tag, chaque Pod sur ce digest, tous "
        "disponibles. Un autre digest, même d'une version voisine, est une autre image.",
    )


# ----------------------------------------------------------------------
# 2. La cause du pull refusé est consignée, avant la réparation.
# ----------------------------------------------------------------------
def test_la_cause_du_pull_refuse_est_consignee_avant_la_reparation(host):
    chemin = f"{_maison(host)}/{NS}/releve.txt"
    f = host.file(chemin)
    contenu = f.content_string if f.exists else ""
    cause = next((ligne.partition(":")[2] for ligne in contenu.splitlines()
                  if ligne.strip().lower().startswith("cause")), "")
    assert CAUSE.search(cause) and REQUETE.search(cause), message(
        en="~/galerie/releve.txt does not say on a cause: line why vignettes cannot pull its image, "
        "as the event of the Pod gives it: the request the registry refuses, and its status code with "
        "the word that goes with it. A general word (secret, credentials) is not enough.",
        fr="~/galerie/releve.txt ne dit pas, sur une ligne cause:, pourquoi vignettes ne tire pas son "
        "image, comme l'événement du Pod le donne : la requête que le registre refuse, et son code de "
        "statut avec le mot qui l'accompagne. Un mot général (secret, identifiants) ne suffit pas.",
    )
    # La réparation se marque par la dernière écriture des identifiants : celle
    # des Secrets de pull que porte le ServiceAccount, et celle du
    # ServiceAccount lui-même. La naissance des Pods n'y suffit pas : le
    # kubelet relit le Secret à chaque nouvelle tentative de pull, et un Pod
    # existant démarre seul une fois le Secret corrigé sur place.
    reparation = _derniere_ecriture_des_identifiants(host)
    ecrit = int(host.check_output(f"stat -c %Y {chemin}"))
    assert reparation is None or ecrit <= reparation, message(
        en="The cause was written, or rewritten, after the repair: ~/galerie/releve.txt is more recent "
        "than the last change of the pull credentials of vignettes. The diagnosis comes first, then the "
        "file is left untouched.",
        fr="La cause a été écrite, ou réécrite, après la réparation : ~/galerie/releve.txt est plus "
        "récent que le dernier changement des identifiants de pull de vignettes. Le diagnostic vient "
        "d'abord, puis on ne touche plus au fichier.",
    )


# ----------------------------------------------------------------------
# 3. vignettes tire son image grâce au ServiceAccount.
# ----------------------------------------------------------------------
def test_vignettes_tire_son_image_grace_a_son_serviceaccount(host):
    sa = _json(host, f"-n {NS} get serviceaccount vignettes") or {}
    noms = [s.get("name") for s in sa.get("imagePullSecrets") or []]
    valides = []
    for nom in noms:
        secret = _json(host, f"-n {NS} get secret {nom}") or {}
        if secret.get("type") == "kubernetes.io/dockerconfigjson":
            res = host.run(f"{ADMIN} -n {NS} get secret {nom} -o jsonpath='{{.data.\\.dockerconfigjson}}' | base64 -d")
            if REGISTRE in res.stdout:
                valides.append(nom)
    d = _json(host, f"-n {NS} get deployment vignettes") or {"spec": {"template": {"spec": {}}}}
    dans_le_template = bool(d["spec"]["template"]["spec"].get("imagePullSecrets"))
    assert valides and not dans_le_template, message(
        en=f"The vignettes ServiceAccount carries no docker-registry Secret for {REGISTRE} "
        f"(found: {noms or 'none'}){', and the Deployment template carries its own' if dans_le_template else ''}. "
        "Expected: the credentials brought by the ServiceAccount, not written into the Pod.",
        fr=f"Le ServiceAccount vignettes ne porte aucun Secret docker-registry pour {REGISTRE} "
        f"(trouvé : {noms or 'aucun'}){', et le template du Deployment porte le sien' if dans_le_template else ''}. "
        "Attendu : les identifiants apportés par le ServiceAccount, pas écrits dans le Pod.",
    )
    d = _attendre_deploiement(host, "vignettes")
    etats = [((c.get("state") or {}).get("waiting") or {}).get("reason") or "en cours"
             for p in _pods(host, "vignettes") for c in (p.get("status") or {}).get("containerStatuses") or []]
    assert d is not None and _disponible(d), message(
        en=f"vignettes is still not available: its Pods are {etats or 'absent'}. Pull Secrets are "
        "injected when a Pod is created.",
        fr=f"vignettes n'est toujours pas disponible : ses Pods sont {etats or 'absents'}. Les Secrets de "
        "pull sont injectés à la création d'un Pod.",
    )
