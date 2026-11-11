"""test_functional.py : k8s-explorer-l-api

Ces tests confrontent le relevé ~/archives/releve.txt à ce que l'API du
cluster « lab » déclare réellement, puis lisent dans le cluster l'objet
Sauvegarde et la sonde du Deployment catalogue. Un test vérifie un seul état
demandé par l'énoncé.

Tous échouent avant le travail : le relevé est vide, aucune Sauvegarde
n'existe et catalogue n'a pas de sonde. L'attente des Pods Ready ne s'ouvre
que si la sonde est déjà posée.

Les messages disent ce qui manque, jamais la commande qui le trouve.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "archives"
APIVERSION = "sauvegarde.formation.k8s/v1beta1"
KIND = "Sauvegarde"
SAUVEGARDE = "commandes-nuit"
#: Les types présents dans archives que `kubectl get all` ne liste pas. Les
#: événements, éphémères, ne sont pas exigés.
CACHES = {"configmaps", "secrets", "serviceaccounts", "roles", "rolebindings", "sauvegardes"}
ATTENTE = 90
PAS = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


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


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _alias(host) -> dict[str, str]:
    """Chaque nom qu'on peut donner à un type, rapporté à son nom pluriel.

    Lu sur le cluster lui-même : nom, abréviations et kind, en minuscules. Un
    apprenant qui écrit `cm`, `ConfigMap` ou `configmaps` désigne le même type.
    """
    res = host.run(f"{ADMIN} api-resources --namespaced=true --no-headers -o wide")
    alias: dict[str, str] = {}
    for ligne in res.stdout.splitlines():
        champs = ligne.split()
        if len(champs) < 4:
            continue
        nom = champs[0]
        # Colonnes : NAME [SHORTNAMES] APIVERSION NAMESPACED KIND VERBS...
        indice_ns = next((i for i, c in enumerate(champs) if c in ("true", "false")), None)
        if indice_ns is None:
            continue
        kind = champs[indice_ns + 1]
        courts = champs[1].split(",") if indice_ns == 3 else []
        for a in [nom, kind, kind + "s", *courts]:
            alias[a.lower()] = nom
    return alias


# ----------------------------------------------------------------------
# 1. Le relevé donne l'apiVersion et le kind de la CRD.
# ----------------------------------------------------------------------
def test_le_releve_donne_l_apiversion_et_le_kind_de_la_crd(releve):
    apiversion, kind = releve.get("apiversion", ""), releve.get("kind", "")
    assert apiversion == APIVERSION and kind == KIND, message(
        en=f"The record gives apiVersion {apiversion or '(empty)'!r} and kind {kind or '(empty)'!r}: "
        "these are not the values to write in a manifest of the backup type installed on the "
        "cluster. The group alone is not enough, the version counts as well.",
        fr=f"Le relevé donne apiVersion {apiversion or '(vide)'!r} et kind {kind or '(vide)'!r} : ce "
        "ne sont pas les valeurs à écrire dans un manifeste du type sauvegarde installé sur le "
        "cluster. Le groupe seul ne suffit pas, la version compte aussi.",
    )


# ----------------------------------------------------------------------
# 2. La sauvegarde demandée existe, avec ses champs obligatoires.
# ----------------------------------------------------------------------
def test_la_sauvegarde_commandes_nuit_existe_avec_les_champs_demandes(host):
    objet = _json(host, f"-n {NS} get sauvegardes.sauvegarde.formation.k8s {SAUVEGARDE}")
    assert objet is not None, message(
        en=f"No Sauvegarde object named {SAUVEGARDE} in {NS}.",
        fr=f"Aucun objet Sauvegarde nommé {SAUVEGARDE} dans {NS}.",
    )
    spec = objet.get("spec") or {}
    cible = spec.get("cible")
    champs = str(spec.get("planification", "")).split()
    a_deux_heures = len(champs) == 5 and champs[0].isdigit() and champs[1].isdigit() \
        and int(champs[0]) == 0 and int(champs[1]) == 2 and champs[2:] == ["*", "*", "*"]
    assert cible == "commandes" and a_deux_heures, message(
        en=f"{SAUVEGARDE} exists, but it does not back up the commandes database every day at "
        f"2:00 (spec found: {spec}). The meaning and the format of each field are in the schema "
        "of the type.",
        fr=f"{SAUVEGARDE} existe, mais elle ne sauvegarde pas la base commandes chaque jour à 2 h "
        f"(spec trouvée : {spec}). Le sens et le format de chaque champ sont dans le schéma du type.",
    )


# ----------------------------------------------------------------------
# 3. catalogue porte une sonde de disponibilité HTTP, et ses Pods sont Ready.
# ----------------------------------------------------------------------
def test_catalogue_porte_une_sonde_de_disponibilite_http(host):
    d = _json(host, f"-n {NS} get deployment catalogue")
    assert d is not None, message(
        en="The catalogue Deployment no longer exists: it must be corrected, not deleted.",
        fr="Le Deployment catalogue n'existe plus : il fallait le corriger, pas le supprimer.",
    )
    conteneur = d["spec"]["template"]["spec"]["containers"][0]
    sonde = (conteneur.get("readinessProbe") or {}).get("httpGet") or {}
    ports = {p.get("name"): p.get("containerPort") for p in conteneur.get("ports") or []}
    port = sonde.get("port")
    port = ports.get(port, port) if isinstance(port, str) else port
    assert port == 80 and sonde.get("path", "/") == "/", message(
        en="catalogue has no readiness probe that queries the root of port 80 over HTTP (found: "
        f"{conteneur.get('readinessProbe') or 'no readiness probe'}).",
        fr="catalogue n'a pas de sonde de disponibilité qui interroge en HTTP la racine du port 80 "
        f"(trouvé : {conteneur.get('readinessProbe') or 'aucune sonde de disponibilité'}).",
    )
    fin = time.monotonic() + ATTENTE
    voulus = d["spec"].get("replicas", 1)
    while time.monotonic() < fin:
        s = d.get("status") or {}
        if s.get("observedGeneration") == d["metadata"]["generation"] \
                and s.get("updatedReplicas") == voulus and s.get("readyReplicas") == voulus:
            break
        time.sleep(PAS)
        d = _json(host, f"-n {NS} get deployment catalogue") or d
    s = d.get("status") or {}
    assert s.get("updatedReplicas") == voulus and s.get("readyReplicas") == voulus, message(
        en=f"catalogue carries the probe, but only {s.get('readyReplicas', 0)} of its {voulus} Pods "
        f"with the new template are Ready after {ATTENTE}s.",
        fr=f"catalogue porte la sonde, mais seuls {s.get('readyReplicas', 0)} de ses {voulus} Pods au "
        f"nouveau template sont Ready après {ATTENTE}s.",
    )


# ----------------------------------------------------------------------
# 4. Le relevé dresse l'inventaire complet du namespace.
# ----------------------------------------------------------------------
def test_le_releve_dresse_l_inventaire_complet_du_namespace(host, releve):
    alias = _alias(host)
    nommes = {alias.get(m.lower(), m.lower()) for m in re.split(r"[\s,;]+", releve.get("inventaire", "")) if m}
    manquants = CACHES - nommes
    assert not manquants, message(
        en=f"The inventory of the record misses {len(manquants)} type(s) of objects present in {NS}. "
        "kubectl get all does not list everything: the inventory must name every type the "
        "namespace holds.",
        fr=f"L'inventaire du relevé omet {len(manquants)} type(s) d'objets présents dans {NS}. "
        "kubectl get all ne liste pas tout : l'inventaire doit nommer chaque type que le "
        "namespace contient.",
    )
