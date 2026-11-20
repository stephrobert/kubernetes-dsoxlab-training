"""test_functional.py : ckad-kustomize-overlays

Ces tests lisent l'état du cluster et, pour deux d'entre eux, le dossier
Kustomize de l'apprenant (~/kustomize/) : un overlay qui ne dérive d'aucune base
ou un cluster qui ne correspond plus au dossier ne se voient pas autrement. Un
test vérifie un seul état demandé par l'énoncé.

Depuis le 2026-11-20, le challenge ne reprend plus les valeurs de la leçon
(dev/prod, préfixes dev-/prod-, 1 et 3 réplicas, label env) : application
catalogue, environnements recette (rec-, 2 réplicas, version 2) et production
(prd-, 4 réplicas, version 1), label palier, et une ConfigMap générée dont
production FUSIONNE une valeur (MODE=ecriture) avec celles de la base
(behavior: merge, montré par la leçon) : l'autre clé de la base doit survivre.

Tous échouent avant le travail : les namespaces recette et production sont
vides et le dossier ~/kustomize/ aussi. L'attente des réplicas ne s'ouvre que
si le Deployment existe déjà.

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

#: Les deux versions de la formation (module 3). La base porte la version 1 ;
#: l'overlay recette, et lui seul, passe à la version 2.
VERSION_1 = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
VERSION_2 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
ENVIRONNEMENTS = {
    "recette": {"prefixe": "rec-", "replicas": 2, "version": VERSION_2, "mode": "lecture"},
    "production": {"prefixe": "prd-", "replicas": 4, "version": VERSION_1, "mode": "ecriture"},
}
APP = "catalogue"
ACCUEIL = "Bienvenue"
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


def _nom(env: str, suffixe: str = "") -> str:
    return f"{ENVIRONNEMENTS[env]['prefixe']}{APP}{suffixe}"


def _deploiement(host, env: str) -> dict | None:
    """Le Deployment de l'environnement, attendu disponible s'il existe déjà."""
    replicas = ENVIRONNEMENTS[env]["replicas"]
    d = _json(host, f"-n {env} get deployment {_nom(env)}")
    fin = time.monotonic() + ATTENTE
    while d is not None and (d.get("status") or {}).get("availableReplicas", 0) != replicas \
            and time.monotonic() < fin:
        time.sleep(PAS)
        d = _json(host, f"-n {env} get deployment {_nom(env)}") or d
    return d


def _verifier_replicas(host, env: str) -> None:
    replicas = ENVIRONNEMENTS[env]["replicas"]
    d = _deploiement(host, env)
    assert d is not None, message(
        en=f"No Deployment {_nom(env)} in the {env} namespace. Its name and its namespace come "
        "from the overlay, not from the base.",
        fr=f"Aucun Deployment {_nom(env)} dans le namespace {env}. Son nom et son namespace "
        "viennent de l'overlay, pas de la base.",
    )
    voulus = d["spec"].get("replicas")
    disponibles = (d.get("status") or {}).get("availableReplicas", 0)
    assert voulus == replicas and disponibles == replicas, message(
        en=f"{_nom(env)} asks for {voulus} replica(s) and has {disponibles} available, expected "
        f"{replicas} and {replicas}. The number of replicas belongs to the overlay.",
        fr=f"{_nom(env)} demande {voulus} réplica(s) et en a {disponibles} disponible(s), attendu "
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
def test_recette_a_deux_replicas_disponibles(host):
    _verifier_replicas(host, "recette")


def test_production_a_quatre_replicas_disponibles(host):
    _verifier_replicas(host, "production")


# ----------------------------------------------------------------------
# 3. Le label de palier atteint les Pods.
# ----------------------------------------------------------------------
def test_les_pods_portent_le_label_de_leur_palier(host):
    for env in ENVIRONNEMENTS:
        pods = (_json(host, f"-n {env} get pods") or {}).get("items", [])
        sans_label = [p["metadata"]["name"] for p in pods
                      if (p["metadata"].get("labels") or {}).get("palier") != env]
        assert pods and not sans_label, message(
            en=f"In {env}, Pods without the label palier={env}: {sans_label or 'no Pod at all'}. "
            "The label must reach the Pod template, not only the Deployment.",
            fr=f"Dans {env}, des Pods sans le label palier={env} : {sans_label or 'aucun Pod'}. Le "
            "label doit atteindre le template des Pods, pas seulement le Deployment.",
        )


# ----------------------------------------------------------------------
# 4. Chaque Service trouve ses Pods.
# ----------------------------------------------------------------------
def test_chaque_service_trouve_ses_pods(host):
    for env, conf in ENVIRONNEMENTS.items():
        service = _nom(env, "-svc")
        tranches = _json(host, f"-n {env} get endpointslices -l kubernetes.io/service-name={service}")
        prets = [a for t in (tranches or {}).get("items", []) for e in t.get("endpoints") or []
                 for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")]
        assert len(prets) == conf["replicas"], message(
            en=f"{service} has {len(prets)} ready endpoint(s), expected {conf['replicas']}. When "
            f"the palier={env} label is on the Pods but not in the Service's selector, or the "
            "other way round, the Service no longer finds its Pods.",
            fr=f"{service} a {len(prets)} endpoint(s) prêt(s), attendu {conf['replicas']}. Quand "
            f"le label palier={env} est sur les Pods mais pas dans le selector du Service, ou "
            "l'inverse, le Service ne trouve plus ses Pods.",
        )


# ----------------------------------------------------------------------
# 5. Les deux environnements ont la même structure, celle de la base.
# ----------------------------------------------------------------------
def test_les_deux_environnements_ont_la_meme_structure(host):
    structures = {}
    for env in ENVIRONNEMENTS:
        d = _json(host, f"-n {env} get deployment {_nom(env)}")
        assert d is not None, message(
            en=f"No Deployment {_nom(env)} to compare.",
            fr=f"Aucun Deployment {_nom(env)} à comparer.",
        )
        c = d["spec"]["template"]["spec"]["containers"][0]
        structures[env] = (c.get("name"), tuple(p.get("containerPort") for p in c.get("ports") or []))
    assert structures["recette"] == structures["production"], message(
        en=f"recette and production differ: {structures}. One base gives the same container and "
        "the same port in both environments.",
        fr=f"recette et production diffèrent : {structures}. Une même base donne le même "
        "conteneur et le même port dans les deux environnements.",
    )


# ----------------------------------------------------------------------
# 6. Seule recette passe à la version 2, par son overlay, sans toucher la base.
# ----------------------------------------------------------------------
def _image(host, env: str) -> str | None:
    d = _json(host, f"-n {env} get deployment {_nom(env)}")
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


def test_recette_passe_a_la_version_2_par_son_overlay(host):
    rec, prd = _image(host, "recette"), _image(host, "production")
    assert _est(rec, VERSION_2) and _est(prd, VERSION_1), message(
        en=f"recette runs {rec!r} and production {prd!r}. Expected: recette on version 2 and "
        "production on version 1, both pinned by digest as in the requirements.",
        fr=f"recette tourne en {rec!r} et production en {prd!r}. Attendu : recette en version 2 "
        "et production en version 1, toutes deux épinglées par digest comme dans le cahier des "
        "charges.",
    )
    base = host.run(f"grep -rhF -e {shlex.quote(VERSION_1.split('@')[1])} "
                    f"-e {shlex.quote(VERSION_2.split('@')[1])} {shlex.quote(_maison(host) + '/kustomize/base')}")
    assert VERSION_1.split("@")[1] in base.stdout and VERSION_2.split("@")[1] not in base.stdout, message(
        en="~/kustomize/base no longer describes version 1 alone: the change of version belongs "
        "to the recette overlay, the base stays as it is.",
        fr="~/kustomize/base ne décrit plus la seule version 1 : le changement de version "
        "appartient à l'overlay recette, la base reste telle quelle.",
    )


# ----------------------------------------------------------------------
# 7. La configuration vient d'un générateur, et production la fusionne.
# ----------------------------------------------------------------------
def test_la_configuration_generee_porte_le_mode_de_chaque_palier(host):
    for env, conf in ENVIRONNEMENTS.items():
        d = _json(host, f"-n {env} get deployment {_nom(env)}")
        refs = [] if d is None else [
            s["configMapRef"]["name"]
            for c in d["spec"]["template"]["spec"]["containers"]
            for s in c.get("envFrom") or [] if s.get("configMapRef")
        ]
        generee = [r for r in refs if re.fullmatch(rf"{_nom(env, '-config')}-[a-z0-9]{{10}}", r)]
        assert generee, message(
            en=f"In {env}, the container does not read a generated ConfigMap "
            f"{_nom(env, '-config')}-<hash> (found {refs or 'none'}). A generated ConfigMap "
            "carries a hash of its content in its name, so that a change of content restarts "
            "the Pods.",
            fr=f"Dans {env}, le conteneur ne lit pas de ConfigMap générée "
            f"{_nom(env, '-config')}-<empreinte> (trouvé {refs or 'aucune'}). Une ConfigMap "
            "générée porte l'empreinte de son contenu dans son nom, pour qu'un changement de "
            "contenu redémarre les Pods.",
        )
        donnees = (_json(host, f"-n {env} get configmap {generee[0]}") or {}).get("data") or {}
        assert donnees.get("MODE") == conf["mode"] and donnees.get("ACCUEIL") == ACCUEIL, message(
            en=f"The ConfigMap {generee[0]} gives MODE={donnees.get('MODE')!r} and "
            f"ACCUEIL={donnees.get('ACCUEIL')!r}, expected MODE={conf['mode']!r} and "
            f"ACCUEIL={ACCUEIL!r}. production changes one value of the base and keeps the other: "
            "a generator in the overlay can merge with the one of the base instead of replacing it.",
            fr=f"La ConfigMap {generee[0]} donne MODE={donnees.get('MODE')!r} et "
            f"ACCUEIL={donnees.get('ACCUEIL')!r}, attendu MODE={conf['mode']!r} et "
            f"ACCUEIL={ACCUEIL!r}. production change une valeur de la base et garde l'autre : un "
            "générateur de l'overlay peut fusionner avec celui de la base au lieu de le remplacer.",
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
    communes = bases["recette"] & bases["production"]
    assert communes, message(
        en="The recette and production overlays do not both reference one and the same base "
        "directory with its own kustomization.yaml: the two environments are described twice.",
        fr="Les overlays recette et production ne référencent pas tous les deux un même dossier "
        "de base portant son propre kustomization.yaml : les deux environnements sont décrits "
        "deux fois.",
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
