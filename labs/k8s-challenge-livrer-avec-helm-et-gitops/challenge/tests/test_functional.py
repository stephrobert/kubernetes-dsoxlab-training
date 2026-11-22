"""test_functional.py : k8s-challenge-livrer-avec-helm-et-gitops

Ces tests lisent l'état du cluster kind « lab », le registre local, la release
Helm et le dépôt Git nu servi à Argo CD. Ils ne lisent jamais les commandes
tapées.

Le contexte de build porte un jeton tiré au sort à la préparation : la page
servie par les Pods doit le montrer, ce qui prouve que l'image qui tourne a été
construite depuis ce contexte, et pas prise ailleurs.

Deux exigences sont bloquantes, parce qu'elles portent le cœur du geste : la
vitrine tourne sur l'image construite, tirée par son digest, et Argo CD suit le
dépôt jusqu'à l'état synchronisé sur son dernier commit.

Tous échouent avant le travail : rien n'est construit, installé ni suivi.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

K = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
HELM = "sudo helm --kubeconfig /etc/kind/lab.kubeconfig"
MEMOIRE = "/var/lib/dsoxlab/challenge-livrer-avec-helm-et-gitops.json"
DEPOT = "/srv/git/catalogue.git"
REGISTRE = "localhost:30500"
NS_VITRINE = "vitrine"
ACCEPT = (
    "application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, "
    "application/vnd.docker.distribution.manifest.v2+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json"
)
BUSYBOX = "busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def dossier(host) -> str:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    return f"{maison}/livraison"


def _json(host, commande: str) -> dict:
    res = host.run(commande)
    if res.rc != 0 or not res.stdout.strip():
        return {}
    return json.loads(res.stdout)


def _digest_du_registre(host) -> str:
    """Le digest de localhost:30500/vitrine:1.0, lu dans le registre lui-même.

    Le registre n'est pas publié sur la VM : on l'interroge depuis un Pod.
    """
    res = host.run(
        f"{K} -n registre run sonde-digest --rm -i --restart=Never --quiet --image={BUSYBOX} -- "
        f"wget -q -S -O /dev/null --header='Accept: {ACCEPT}' "
        "http://registre.registre:5000/v2/vitrine/manifests/1.0 2>&1"
    )
    for ligne in res.stdout.splitlines():
        if ligne.strip().lower().startswith("docker-content-digest:"):
            return ligne.split(":", 1)[1].strip()
    return ""


def _pods_vitrine(host) -> list[dict]:
    return _json(host, f"{K} -n {NS_VITRINE} get pods -l app=vitrine -o json").get("items", [])


def _historique(host) -> list[dict]:
    res = host.run(f"{HELM} -n {NS_VITRINE} history vitrine -o json")
    return json.loads(res.stdout) if res.rc == 0 and res.stdout.strip() else []


def _application(host) -> dict:
    return _json(host, f"{K} -n argocd get applications.argoproj.io catalogue -o json")


def _tete_du_depot(host) -> str:
    return host.run(f"sudo git --git-dir={DEPOT} rev-parse main").stdout.strip()


# ----------------------------------------------------------------------
# 1. L'image est construite depuis le contexte et poussée au registre.
# ----------------------------------------------------------------------
def test_l_image_est_construite_et_poussee(host, memoire):
    digest = _digest_du_registre(host)
    page = host.run(
        f"{K} -n {NS_VITRINE} run sonde-page --rm -i --restart=Never --quiet --image={BUSYBOX} -- "
        f"wget -q -O - -T 5 http://vitrine.{NS_VITRINE}/"
    ).stdout
    assert digest and memoire["jeton"] in page, message(
        en=f"The registry holds {'vitrine:1.0' if digest else 'no vitrine:1.0'}, and the page served by vitrine "
        f"{'shows' if memoire['jeton'] in page else 'does not show'} the build of ~/livraison/app. Expected the "
        f"image built from ~/livraison/app, pushed as {REGISTRE}/vitrine:1.0, and served by the release.",
        fr=f"Le registre {'porte' if digest else 'ne porte pas'} vitrine:1.0, et la page servie par vitrine "
        f"{'montre' if memoire['jeton'] in page else 'ne montre pas'} la construction de ~/livraison/app. Attendu "
        f"l'image construite depuis ~/livraison/app, poussée en {REGISTRE}/vitrine:1.0, et servie par la release.",
    )


# ----------------------------------------------------------------------
# 2. La release est installée avec le fichier de values.
# ----------------------------------------------------------------------
def test_la_release_est_installee_avec_le_fichier_de_values(host, dossier):
    fichier = host.run(f"cat {dossier}/values-vitrine.yaml")
    attendu = yaml.safe_load(fichier.stdout) if fichier.rc == 0 else None
    vues = _json(host, f"{HELM} -n {NS_VITRINE} get values vitrine --revision 1 -o json")
    assert attendu and vues == attendu and attendu.get("replicaCount") == 2, message(
        en=f"Revision 1 of the release vitrine was installed with {vues or 'nothing'}, the file "
        f"~/livraison/values-vitrine.yaml holds {attendu or 'nothing'}. Expected the release installed in the "
        "vitrine namespace from that file, with 2 copies.",
        fr=f"La révision 1 de la release vitrine a été installée avec {vues or 'rien'}, le fichier "
        f"~/livraison/values-vitrine.yaml porte {attendu or 'rien'}. Attendu la release installée dans le "
        "namespace vitrine depuis ce fichier, avec 2 exemplaires.",
    )


# ----------------------------------------------------------------------
# 3. La vitrine tourne sur l'image construite, tirée par digest. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_vitrine_tourne_par_digest(host):
    digest = _digest_du_registre(host)
    pods = _pods_vitrine(host)
    images = sorted({c["image"] for p in pods for c in p["spec"]["containers"]})
    prets = [p for p in pods if all(s.get("ready") for s in p.get("status", {}).get("containerStatuses", []))]
    attendue = f"{REGISTRE}/vitrine@{digest}"
    cible_en = attendue if digest else "the image of the registry, by its digest"
    cible_fr = attendue if digest else "l'image du registre, par son digest"
    assert digest and images == [attendue] and len(prets) == 2, message(
        en=f"The vitrine Pods run {images or 'nothing'} ({len(prets)} ready). Expected 2 ready Pods on "
        f"{cible_en}: a tag can be moved, a digest cannot.",
        fr=f"Les Pods de vitrine font tourner {images or 'rien'} ({len(prets)} prêt(s)). Attendu 2 Pods prêts "
        f"sur {cible_fr} : un tag se déplace, un digest non.",
    )


# ----------------------------------------------------------------------
# 4. La mise à jour, puis le retour à la révision 1.
# ----------------------------------------------------------------------
def test_la_release_est_mise_a_jour_puis_ramenee_a_la_revision_1(host):
    historique = _historique(host)
    revisions = {r["revision"]: r for r in historique}
    deux = _json(host, f"{HELM} -n {NS_VITRINE} get values vitrine --revision 2 -o json")
    derniere = historique[-1] if historique else {}
    assert (
        revisions.get(2, {}).get("description", "").startswith("Upgrade")
        and deux.get("replicaCount") == 3
        and derniere.get("status") == "deployed"
        and derniere.get("description") == "Rollback to 1"
    ), message(
        en="The history of vitrine is " + "; ".join(f"{r['revision']} {r['description']}" for r in historique)
        + f", revision 2 asks {deux.get('replicaCount', '?')} copies. Expected an upgrade to 3 copies as revision 2, "
        "then the release brought back to revision 1, which is what is deployed now.",
        fr="L'historique de vitrine est " + "; ".join(f"{r['revision']} {r['description']}" for r in historique)
        + f", la révision 2 demande {deux.get('replicaCount', '?')} exemplaire(s). Attendu une mise à jour à 3 "
        "exemplaires en révision 2, puis la release ramenée à la révision 1, qui est celle déployée maintenant.",
    )


# ----------------------------------------------------------------------
# 5. Argo CD suit le dépôt, synchronisé sur son dernier commit. BLOQUANT.
# ----------------------------------------------------------------------
def test_argo_cd_suit_le_depot_jusqu_a_la_synchro(host, memoire):
    app = _application(host)
    spec = app.get("spec", {})
    source = spec.get("source", {})
    statut = app.get("status", {})
    tete = _tete_du_depot(host)
    vu = (
        f"dépôt {source.get('repoURL', '?')}, chemin {source.get('path', '?')}, "
        f"namespace {spec.get('destination', {}).get('namespace', '?')}, "
        f"synchro {'automatique' if spec.get('syncPolicy', {}).get('automated') is not None else 'manuelle'}, "
        f"{statut.get('sync', {}).get('status', '?')} / {statut.get('health', {}).get('status', '?')} "
        f"sur {statut.get('sync', {}).get('revision', '?')[:12]}"
    )
    assert (
        source.get("repoURL") == memoire["depot"]
        and source.get("path", "").strip("/") == "catalogue"
        and spec.get("destination", {}).get("namespace") == "catalogue"
        and spec.get("syncPolicy", {}).get("automated") is not None
        and statut.get("sync", {}).get("status") == "Synced"
        and statut.get("health", {}).get("status") == "Healthy"
        and statut.get("sync", {}).get("revision") == tete
    ), message(
        en=f"The Argo CD Application catalogue: {vu if app else 'absent'}. Expected it to follow "
        f"{memoire['depot']} (path catalogue) into the catalogue namespace, with automated sync, Synced and "
        f"Healthy on the last commit of the repository ({tete[:12]}).",
        fr=f"L'Application Argo CD catalogue : {vu if app else 'absente'}. Attendu qu'elle suive "
        f"{memoire['depot']} (chemin catalogue) vers le namespace catalogue, en synchro automatique, Synced et "
        f"Healthy sur le dernier commit du dépôt ({tete[:12]}).",
    )


# ----------------------------------------------------------------------
# 6. Le changement passe par Git.
# ----------------------------------------------------------------------
def test_le_changement_passe_par_git(host):
    manifeste = host.run(f"sudo git --git-dir={DEPOT} show main:catalogue/deployment.yaml").stdout
    dans_git = (yaml.safe_load(manifeste) or {}).get("spec", {}).get("replicas") if manifeste else None
    commits = host.run(f"sudo git --git-dir={DEPOT} rev-list --count main").stdout.strip()
    deploiement = _json(host, f"{K} -n catalogue get deployment catalogue -o json")
    disponibles = deploiement.get("status", {}).get("availableReplicas", 0)
    assert dans_git == 2 and commits.isdigit() and int(commits) >= 2 and disponibles == 2, message(
        en=f"The repository asks {dans_git} copy(ies) of catalogue ({commits or '?'} commit(s)), and the cluster "
        f"runs {disponibles}. Expected 2 copies, written in Git, pushed, and applied by Argo CD.",
        fr=f"Le dépôt demande {dans_git} exemplaire(s) de catalogue ({commits or '?'} commit(s)), et le cluster "
        f"en fait tourner {disponibles}. Attendu 2 exemplaires, écrits dans Git, poussés, et appliqués par "
        "Argo CD.",
    )
