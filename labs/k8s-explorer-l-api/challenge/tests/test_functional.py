"""test_functional.py : k8s-explorer-l-api

Ces tests confrontent le relevé ~/entrepot/releve.txt à ce que l'API du
cluster « lab » déclare réellement, puis lisent dans le cluster l'objet Export
et la sonde du Deployment annuaire. Un test vérifie un seul état demandé par
l'énoncé.

Depuis le 2026-11-20, le challenge ne reprend plus la démonstration de la
leçon (une CRD à une version, une sonde sur la racine du port 80). La CRD
Export est servie en DEUX versions, v1alpha1 et v1 : seule v1, la version que
sert `api-resources`, porte les champs obligatoires et la liste fermée du
format. La sonde vise /healthz sur le port nommé web (8080). Le namespace
contient des types que `kubectl get all` ne montre pas et que la leçon ne
crée pas : ResourceQuota, NetworkPolicy, PodDisruptionBudget.

Tous échouent avant le travail : le relevé est vide, aucun Export n'existe et
annuaire n'a pas de sonde. L'attente des Pods Ready ne s'ouvre que si la sonde
est déjà posée.

Les messages disent ce qui manque, jamais la commande qui le trouve.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "entrepot"
APIVERSION = "donnees.formation.k8s/v1"
KIND = "Export"
EXPORT = "ventes-hebdo"
#: Les types présents dans entrepot que `kubectl get all` ne montre pas. Le
#: type Export n'y est qu'une fois l'objet ventes-hebdo créé par l'apprenant.
CACHES = {"configmaps", "secrets", "serviceaccounts", "resourcequotas",
          "networkpolicies", "poddisruptionbudgets", "exports"}
ATTENTE = 90
PAS = 3
LUNDI = {"1", "mon"}


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

    Lu sur le cluster lui-même : nom, abréviations et kind, en minuscules, seuls
    ou suivis du groupe. Un apprenant qui écrit `cm`, `ConfigMap`,
    `configmaps`, `roles.rbac.authorization.k8s.io` ou `Export.donnees.formation.k8s`
    désigne un type que le cluster connaît. Avant le 2026-11-20, les formes
    suivies du groupe, celles qu'écrit la boucle de la leçon, étaient refusées.
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
        version = champs[indice_ns - 1]
        groupe = version.split("/")[0] if "/" in version else ""
        courts = champs[1].split(",") if indice_ns == 3 else []
        for a in [nom, kind, kind + "s", *courts]:
            alias[a.lower()] = nom
            if groupe:
                alias[f"{a}.{groupe}".lower()] = nom
    return alias


# ----------------------------------------------------------------------
# 1. Le relevé donne l'apiVersion et le kind de la CRD.
# ----------------------------------------------------------------------
def test_le_releve_donne_l_apiversion_et_le_kind_de_la_crd(releve):
    apiversion, kind = releve.get("apiversion", ""), releve.get("kind", "")
    assert apiversion == APIVERSION and kind == KIND, message(
        en=f"The record gives apiVersion {apiversion or '(empty)'!r} and kind {kind or '(empty)'!r}: "
        "these are not the values to write in a manifest of the export type installed on the "
        "cluster. The group alone is not enough, the version counts as well: this type is "
        "served in more than one version, and the cluster says which one it serves by default.",
        fr=f"Le relevé donne apiVersion {apiversion or '(vide)'!r} et kind {kind or '(vide)'!r} : ce "
        "ne sont pas les valeurs à écrire dans un manifeste du type export installé sur le "
        "cluster. Le groupe seul ne suffit pas, la version compte aussi : ce type est servi en "
        "plusieurs versions, et le cluster dit laquelle il sert par défaut.",
    )


# ----------------------------------------------------------------------
# 2. L'export demandé existe, avec ses champs obligatoires.
# ----------------------------------------------------------------------
def _chaque_lundi_a_3h30(planification: str) -> bool:
    champs = planification.split()
    return (len(champs) == 5 and champs[0].isdigit() and champs[1].isdigit()
            and int(champs[0]) == 30 and int(champs[1]) == 3
            and champs[2:4] == ["*", "*"] and champs[4].lower() in LUNDI)


def test_l_export_ventes_hebdo_existe_avec_les_champs_demandes(host):
    objet = _json(host, f"-n {NS} get exports.donnees.formation.k8s {EXPORT}")
    assert objet is not None, message(
        en=f"No Export object named {EXPORT} in {NS}.",
        fr=f"Aucun objet Export nommé {EXPORT} dans {NS}.",
    )
    spec = objet.get("spec") or {}
    assert (spec.get("base") == "ventes" and spec.get("format") == "parquet"
            and _chaque_lundi_a_3h30(str(spec.get("planification", "")))), message(
        en=f"{EXPORT} exists, but it does not export the ventes database in parquet every Monday "
        f"at 3:30 (spec found: {spec}). The meaning, the format and the allowed values of each "
        "field are in the schema of the type, in the version the cluster serves.",
        fr=f"{EXPORT} existe, mais il n'exporte pas la base ventes en parquet chaque lundi à "
        f"3 h 30 (spec trouvée : {spec}). Le sens, le format et les valeurs permises de chaque "
        "champ sont dans le schéma du type, dans la version que sert le cluster.",
    )


# ----------------------------------------------------------------------
# 3. annuaire porte une sonde de disponibilité HTTP, et ses Pods sont Ready.
# ----------------------------------------------------------------------
def test_annuaire_porte_une_sonde_de_disponibilite_http(host):
    d = _json(host, f"-n {NS} get deployment annuaire")
    assert d is not None, message(
        en="The annuaire Deployment no longer exists: it must be corrected, not deleted.",
        fr="Le Deployment annuaire n'existe plus : il fallait le corriger, pas le supprimer.",
    )
    conteneur = d["spec"]["template"]["spec"]["containers"][0]
    sonde = (conteneur.get("readinessProbe") or {}).get("httpGet") or {}
    ports = {p.get("name"): p.get("containerPort") for p in conteneur.get("ports") or []}
    port = sonde.get("port")
    port = ports.get(port, port) if isinstance(port, str) else port
    assert port == 8080 and sonde.get("path") == "/healthz", message(
        en="annuaire has no readiness probe that queries /healthz over HTTP on the web port "
        f"(8080) (found: {conteneur.get('readinessProbe') or 'no readiness probe'}).",
        fr="annuaire n'a pas de sonde de disponibilité qui interroge en HTTP /healthz sur le port "
        f"web (8080) (trouvé : {conteneur.get('readinessProbe') or 'aucune sonde de disponibilité'}).",
    )
    fin = time.monotonic() + ATTENTE
    voulus = d["spec"].get("replicas", 1)
    while time.monotonic() < fin:
        s = d.get("status") or {}
        if s.get("observedGeneration") == d["metadata"]["generation"] \
                and s.get("updatedReplicas") == voulus and s.get("readyReplicas") == voulus:
            break
        time.sleep(PAS)
        d = _json(host, f"-n {NS} get deployment annuaire") or d
    s = d.get("status") or {}
    assert s.get("updatedReplicas") == voulus and s.get("readyReplicas") == voulus, message(
        en=f"annuaire carries the probe, but only {s.get('readyReplicas', 0)} of its {voulus} Pods "
        f"with the new template are Ready after {ATTENTE}s.",
        fr=f"annuaire porte la sonde, mais seuls {s.get('readyReplicas', 0)} de ses {voulus} Pods au "
        f"nouveau template sont Ready après {ATTENTE}s.",
    )


# ----------------------------------------------------------------------
# 4. Le relevé dresse l'inventaire complet du namespace.
# ----------------------------------------------------------------------
def test_le_releve_dresse_l_inventaire_complet_du_namespace(host, releve):
    alias = _alias(host)
    nommes = {alias.get(m.lower(), m.lower())
              for m in re.split(r"[\s,;]+", releve.get("inventaire", "")) if m}
    manquants = CACHES - nommes
    assert not manquants, message(
        en=f"The inventory of the record misses {len(manquants)} type(s) of objects present in {NS}. "
        "kubectl get all does not list everything: the inventory must name every type the "
        "namespace holds.",
        fr=f"L'inventaire du relevé omet {len(manquants)} type(s) d'objets présents dans {NS}. "
        "kubectl get all ne liste pas tout : l'inventaire doit nommer chaque type que le "
        "namespace contient.",
    )
