"""test_functional.py : k8s-gerer-les-images

Ces tests lisent dans le cluster « lab » l'image d'affiche et le digest que ses
Pods font tourner, comparé à celui que le setup a mémorisé ; le relevé
~/galerie/releve.txt et sa date, comparée à celle du Secret qui répare
vignettes ; puis d'où vient le Secret de pull de vignettes. Un test vérifie un
seul état demandé par l'énoncé.

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
#: Ce qui dit la cause d'un pull refusé par un registre privé : l'état que
#: Kubernetes affiche, ou une phrase qui parle d'authentification.
CAUSE = re.compile(
    r"auth|credential|identifiant|401|unauthori[sz]ed|mot de passe|password|access denied|accès refusé"
    r"|imagepullsecret|docker-registry|secret",
    re.IGNORECASE,
)
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
    assert CAUSE.search(cause), message(
        en="~/galerie/releve.txt does not say on a cause: line why vignettes cannot pull its image: "
        "what the registry expects and does not receive.",
        fr="~/galerie/releve.txt ne dit pas, sur une ligne cause:, pourquoi vignettes ne tire pas son "
        "image : ce que le registre attend et ne reçoit pas.",
    )
    sa = _json(host, f"-n {NS} get serviceaccount vignettes") or {}
    noms = [s.get("name") for s in sa.get("imagePullSecrets") or []]
    dates = []
    for nom in noms:
        secret = _json(host, f"-n {NS} get secret {nom}")
        if secret:
            dates.append(datetime.fromisoformat(secret["metadata"]["creationTimestamp"].replace("Z", "+00:00")).timestamp())
    ecrit = int(host.check_output(f"stat -c %Y {chemin}"))
    assert not dates or ecrit <= min(dates), message(
        en="The cause was written, or rewritten, after the repair: ~/galerie/releve.txt is more recent "
        "than the pull Secret. The diagnosis comes first, then the file is left untouched.",
        fr="La cause a été écrite, ou réécrite, après la réparation : ~/galerie/releve.txt est plus "
        "récent que le Secret de pull. Le diagnostic vient d'abord, puis on ne touche plus au fichier.",
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
