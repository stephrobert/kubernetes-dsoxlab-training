"""test_functional.py : ckad-kustomize-overlays

Ces tests lisent l'état du cluster et, pour deux d'entre eux, le dossier
Kustomize de l'apprenant (~/kustomize/) : un overlay qui ne dérive d'aucune base
ou un cluster qui ne correspond plus au dossier ne se voient pas autrement. Un
test vérifie un seul état demandé par l'énoncé.

Tous échouent avant le travail : les namespaces dev et prod sont vides et le
dossier ~/kustomize/ aussi. L'attente des réplicas ne s'ouvre que si le
Deployment existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import shlex
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

ENVIRONNEMENTS = {"dev": 1, "prod": 3}
#: Les deux versions de la formation (module 3). La base porte la version 1 ;
#: l'overlay dev, et lui seul, passe à la version 2.
VERSION_1 = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
VERSION_2 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 90
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{KUBECTL} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _deploiement(host, env: str, replicas: int) -> dict | None:
    """Le Deployment de l'environnement, attendu disponible s'il existe déjà."""
    d = _json(host, f"-n {env} get deployment {env}-app")
    fin = time.monotonic() + ATTENTE
    while d is not None and (d.get("status") or {}).get("availableReplicas", 0) != replicas \
            and time.monotonic() < fin:
        time.sleep(PAS)
        d = _json(host, f"-n {env} get deployment {env}-app") or d
    return d


def _verifier_replicas(host, env: str, replicas: int) -> None:
    d = _deploiement(host, env, replicas)
    assert d is not None, message(
        en=f"No Deployment {env}-app in the {env} namespace. Its name and its namespace come "
        "from the overlay, not from the base.",
        fr=f"Aucun Deployment {env}-app dans le namespace {env}. Son nom et son namespace "
        "viennent de l'overlay, pas de la base.",
    )
    voulus = d["spec"].get("replicas")
    disponibles = (d.get("status") or {}).get("availableReplicas", 0)
    assert voulus == replicas and disponibles == replicas, message(
        en=f"{env}-app asks for {voulus} replica(s) and has {disponibles} available, expected "
        f"{replicas} and {replicas}. The number of replicas belongs to the overlay.",
        fr=f"{env}-app demande {voulus} réplica(s) et en a {disponibles} disponible(s), attendu "
        f"{replicas} et {replicas}. Le nombre de réplicas appartient à l'overlay.",
    )


def _kustomization(host, chemin: str) -> dict | None:
    fichier = host.file(chemin)
    if not fichier.exists:
        return None
    try:
        return yaml.safe_load(fichier.content_string) or {}
    except yaml.YAMLError:
        return None


# ----------------------------------------------------------------------
# 1 et 2. Chaque environnement tourne avec son nombre de réplicas.
# ----------------------------------------------------------------------
def test_dev_a_un_replica_disponible(host):
    _verifier_replicas(host, "dev", 1)


def test_prod_a_trois_replicas_disponibles(host):
    _verifier_replicas(host, "prod", 3)


# ----------------------------------------------------------------------
# 3. Le label d'environnement atteint les Pods.
# ----------------------------------------------------------------------
def test_les_pods_portent_le_label_de_leur_environnement(host):
    for env in ENVIRONNEMENTS:
        pods = (_json(host, f"-n {env} get pods") or {}).get("items", [])
        sans_label = [p["metadata"]["name"] for p in pods
                      if (p["metadata"].get("labels") or {}).get("env") != env]
        assert pods and not sans_label, message(
            en=f"In {env}, Pods without the label env={env}: {sans_label or 'no Pod at all'}. The "
            "label must reach the Pod template, not only the Deployment.",
            fr=f"Dans {env}, des Pods sans le label env={env} : {sans_label or 'aucun Pod'}. Le "
            "label doit atteindre le template des Pods, pas seulement le Deployment.",
        )


# ----------------------------------------------------------------------
# 4. Chaque Service trouve ses Pods.
# ----------------------------------------------------------------------
def test_chaque_service_trouve_ses_pods(host):
    for env, replicas in ENVIRONNEMENTS.items():
        service = f"{env}-app-svc"
        tranches = _json(host, f"-n {env} get endpointslices -l kubernetes.io/service-name={service}")
        prets = [a for t in (tranches or {}).get("items", []) for e in t.get("endpoints") or []
                 for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")]
        assert len(prets) == replicas, message(
            en=f"{service} has {len(prets)} ready endpoint(s), expected {replicas}. When the "
            f"env={env} label is on the Pods but not in the Service's selector, or the other way "
            "round, the Service no longer finds its Pods.",
            fr=f"{service} a {len(prets)} endpoint(s) prêt(s), attendu {replicas}. Quand le label "
            f"env={env} est sur les Pods mais pas dans le selector du Service, ou l'inverse, le "
            "Service ne trouve plus ses Pods.",
        )


# ----------------------------------------------------------------------
# 5. Les deux environnements ont la même structure, celle de la base.
# ----------------------------------------------------------------------
def test_les_deux_environnements_ont_la_meme_structure(host):
    structures = {}
    for env in ENVIRONNEMENTS:
        d = _json(host, f"-n {env} get deployment {env}-app")
        assert d is not None, message(
            en=f"No Deployment {env}-app to compare.",
            fr=f"Aucun Deployment {env}-app à comparer.",
        )
        c = d["spec"]["template"]["spec"]["containers"][0]
        structures[env] = (c.get("name"), tuple(p.get("containerPort") for p in c.get("ports") or []))
    assert structures["dev"] == structures["prod"], message(
        en=f"dev and prod differ: {structures}. One base gives the same container and the same "
        "port in both environments.",
        fr=f"dev et prod diffèrent : {structures}. Une même base donne le même conteneur et le "
        "même port dans les deux environnements.",
    )


# ----------------------------------------------------------------------
# 6. Seul dev passe à la version 2, par son overlay, sans toucher la base.
# ----------------------------------------------------------------------
def _image(host, env: str) -> str | None:
    d = _json(host, f"-n {env} get deployment {env}-app")
    return None if d is None else d["spec"]["template"]["spec"]["containers"][0].get("image")


def _est(image: str | None, version: str) -> bool:
    """`image` désigne-t-elle `version` ? Même dépôt, même digest, tag facultatif.

    Mesuré le 2026-11-11 avec Kustomize v5.8.1 : `images` avec `digest` seul rend
    nginx@sha256:..., avec `newTag` rend nginx:1.30.6@sha256:... ; les deux
    épinglent la même image, et le test ne doit refuser ni l'un ni l'autre.
    """
    if not image or "@" not in image:
        return False
    nom_tag, digest = image.split("@", 1)
    attendu_nom_tag, attendu_digest = version.split("@", 1)
    depot = nom_tag.removeprefix("docker.io/library/").split(":")[0]
    tag = nom_tag.split(":")[1] if ":" in nom_tag.rsplit("/", 1)[-1] else None
    return depot == attendu_nom_tag.split(":")[0] and digest == attendu_digest \
        and tag in (None, attendu_nom_tag.split(":")[1])


def test_dev_passe_a_la_version_2_par_son_overlay(host):
    dev, prod = _image(host, "dev"), _image(host, "prod")
    assert _est(dev, VERSION_2) and _est(prod, VERSION_1), message(
        en=f"dev runs {dev!r} and prod {prod!r}. Expected: dev on version 2 and prod on version "
        "1, both pinned by digest as in the requirements.",
        fr=f"dev tourne en {dev!r} et prod en {prod!r}. Attendu : dev en version 2 et prod en "
        "version 1, toutes deux épinglées par digest comme dans le cahier des charges.",
    )
    base = host.run(f"grep -rhF -e {shlex.quote(VERSION_1.split('@')[1])} "
                    f"-e {shlex.quote(VERSION_2.split('@')[1])} {shlex.quote(_maison(host) + '/kustomize/base')}")
    assert VERSION_1.split("@")[1] in base.stdout and VERSION_2.split("@")[1] not in base.stdout, message(
        en="~/kustomize/base no longer describes version 1 alone: the change of version belongs "
        "to the dev overlay, the base stays as it is.",
        fr="~/kustomize/base ne décrit plus la seule version 1 : le changement de version "
        "appartient à l'overlay dev, la base reste telle quelle.",
    )


# ----------------------------------------------------------------------
# 7. La configuration vient d'un générateur.
# ----------------------------------------------------------------------
def test_la_configuration_vient_d_une_configmap_generee(host):
    for env in ENVIRONNEMENTS:
        d = _json(host, f"-n {env} get deployment {env}-app")
        refs = [] if d is None else [
            s["configMapRef"]["name"]
            for c in d["spec"]["template"]["spec"]["containers"]
            for s in c.get("envFrom") or [] if s.get("configMapRef")
        ]
        generee = [r for r in refs if re.fullmatch(rf"{env}-app-config-[a-z0-9]{{10}}", r)]
        assert generee, message(
            en=f"In {env}, the container does not read a generated ConfigMap {env}-app-config-<hash> "
            f"(found {refs or 'none'}). A generated ConfigMap carries a hash of its content in its "
            "name, so that a change of content restarts the Pods.",
            fr=f"Dans {env}, le conteneur ne lit pas de ConfigMap générée {env}-app-config-<empreinte> "
            f"(trouvé {refs or 'aucune'}). Une ConfigMap générée porte l'empreinte de son contenu "
            "dans son nom, pour qu'un changement de contenu redémarre les Pods.",
        )
        cm = _json(host, f"-n {env} get configmap {generee[0]}") or {}
        valeur = (cm.get("data") or {}).get("MESSAGE")
        assert valeur == "Bienvenue", message(
            en=f"The ConfigMap {generee[0]} gives MESSAGE={valeur!r}, expected 'Bienvenue'.",
            fr=f"La ConfigMap {generee[0]} donne MESSAGE={valeur!r}, attendu 'Bienvenue'.",
        )


# ----------------------------------------------------------------------
# 8. Les deux overlays dérivent d'une même base.
# ----------------------------------------------------------------------
def test_les_overlays_derivent_d_une_meme_base(host):
    maison = _maison(host)
    bases = {}
    for env in ENVIRONNEMENTS:
        dossier = f"{maison}/kustomize/overlays/{env}"
        k = _kustomization(host, f"{dossier}/kustomization.yaml")
        assert k is not None, message(
            en=f"No readable ~/kustomize/overlays/{env}/kustomization.yaml.",
            fr=f"Aucun ~/kustomize/overlays/{env}/kustomization.yaml lisible.",
        )
        cibles = set()
        for ressource in k.get("resources") or []:
            res = host.run(f"realpath -e {shlex.quote(dossier + '/' + str(ressource))}")
            chemin = res.stdout.strip()
            if res.rc == 0 and host.file(f"{chemin}/kustomization.yaml").exists:
                cibles.add(chemin)
        bases[env] = cibles
    communes = bases["dev"] & bases["prod"]
    assert communes, message(
        en="The dev and prod overlays do not both reference one and the same base directory "
        "with its own kustomization.yaml: the two environments are described twice.",
        fr="Les overlays dev et prod ne référencent pas tous les deux un même dossier de base "
        "portant son propre kustomization.yaml : les deux environnements sont décrits deux fois.",
    )


# ----------------------------------------------------------------------
# 9. Le cluster correspond au dossier versionné.
# ----------------------------------------------------------------------
def test_le_cluster_correspond_aux_overlays(host):
    maison = _maison(host)
    for env in ENVIRONNEMENTS:
        res = host.run(f"{KUBECTL} diff -k {shlex.quote(f'{maison}/kustomize/overlays/{env}')}")
        assert res.rc == 0, message(
            en=f"The cluster does not match ~/kustomize/overlays/{env}: a comparison of the "
            f"overlay with the cluster finds differences, or cannot be made (code {res.rc}).",
            fr=f"Le cluster ne correspond pas à ~/kustomize/overlays/{env} : la comparaison de "
            f"l'overlay avec le cluster trouve des différences, ou ne peut pas se faire "
            f"(code {res.rc}).",
        )
