"""test_functional.py : k8s-extraire-avec-kubectl

Ces tests confrontent les extractions de l'apprenant à l'état réel : l'image
du modèle de Pod du Deployment web, et le couple (Pod, nœud) de chaque Pod de
web. Un test vérifie un seul état demandé par l'énoncé.

Le setup a mis web en pause avant de changer son image : le modèle dit 1.30.6,
les Pods tournent encore en 1.30.5. La valeur consignée doit être celle du
modèle. Les deux listes se distinguent par leur forme : JSONPath n'écrit pas
d'en-tête, custom-columns en écrit un.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "extraction"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _couples_reels(host) -> set[tuple[str, str]]:
    pods = (_json(host, "get pods -l app=web") or {}).get("items") or []
    return {(p["metadata"]["name"], p["spec"].get("nodeName", ""))
            for p in pods if not p["metadata"].get("deletionTimestamp")}


def _lignes(host, nom: str) -> list[list[str]] | None:
    fichier = host.file(f"{_maison(host)}/{NS}/{nom}")
    if not fichier.exists:
        return None
    return [ligne.split() for ligne in fichier.content_string.splitlines() if ligne.strip()]


# ----------------------------------------------------------------------
# 1. L'image du modèle de Pod.
# ----------------------------------------------------------------------
def test_l_image_du_modele_de_web_est_consignee(host):
    fichier = host.file(f"{_maison(host)}/{NS}/releve.txt")
    valeur = ""
    if fichier.exists:
        for ligne in fichier.content_string.splitlines():
            if ligne.strip().lower().startswith("image-modele:"):
                valeur = ligne.split(":", 1)[1].strip().strip("`'\"")
    assert valeur, message(
        en=f"The key 'image-modele' of ~/{NS}/releve.txt has no value.",
        fr=f"La clé 'image-modele' de ~/{NS}/releve.txt n'a pas de valeur.",
    )
    dep = _json(host, "get deployment web")
    assert dep is not None, message(
        en=f"No Deployment web in {NS}: run dsoxlab reset k8s-extraire-avec-kubectl.",
        fr=f"Aucun Deployment web dans {NS} : lancez dsoxlab reset k8s-extraire-avec-kubectl.",
    )
    attendue = dep["spec"]["template"]["spec"]["containers"][0].get("image", "")
    assert valeur == attendue, message(
        en=f"image-modele is {valeur!r}, whereas the Pod template of web asks for {attendue!r}. "
        "The image of a running Pod is not always the one the Deployment asks for: read the "
        "Deployment itself, at .spec.template.spec.containers[0].image.",
        fr=f"image-modele vaut {valeur!r}, alors que le modèle de Pod de web demande "
        f"{attendue!r}. L'image d'un Pod en marche n'est pas toujours celle que demande le "
        "Deployment : lisez le Deployment lui-même, en .spec.template.spec.containers[0].image.",
    )


# ----------------------------------------------------------------------
# 2. La liste en JSONPath.
# ----------------------------------------------------------------------
def test_la_liste_jsonpath_donne_chaque_pod_et_son_noeud(host):
    lignes = _lignes(host, "pods-jsonpath.txt")
    assert lignes, message(
        en=f"~/{NS}/pods-jsonpath.txt is missing or empty.",
        fr=f"~/{NS}/pods-jsonpath.txt est absent ou vide.",
    )
    reels = _couples_reels(host)
    lus = {(c[0], c[1]) for c in lignes if len(c) == 2}
    assert all(len(c) == 2 for c in lignes) and lus == reels, message(
        en=f"pods-jsonpath.txt holds {lignes}, expected exactly one line per web Pod, the Pod "
        f"then its node: {sorted(reels)}. On a list, the objects are under .items, and range "
        "... end repeats a pattern for each one, without header.",
        fr=f"pods-jsonpath.txt contient {lignes}, attendu exactement une ligne par Pod de web, le "
        f"Pod puis son nœud : {sorted(reels)}. Sur une liste, les objets sont sous .items, et "
        "range ... end répète un motif pour chacun, sans en-tête.",
    )


# ----------------------------------------------------------------------
# 3. La liste en custom-columns.
# ----------------------------------------------------------------------
def test_la_liste_custom_columns_donne_chaque_pod_et_son_noeud(host):
    lignes = _lignes(host, "pods-colonnes.txt")
    assert lignes, message(
        en=f"~/{NS}/pods-colonnes.txt is missing or empty.",
        fr=f"~/{NS}/pods-colonnes.txt est absent ou vide.",
    )
    reels = _couples_reels(host)
    noms = {nom for nom, _ in reels}
    entete, corps = lignes[0], lignes[1:]
    lus = {(c[0], c[1]) for c in corps if len(c) == 2}
    assert len(entete) == 2 and entete[0] not in noms and all(len(c) == 2 for c in corps) and lus == reels, message(
        en=f"pods-colonnes.txt holds {lignes}, expected a header line with two column titles, "
        f"then one line per web Pod, the Pod then its node: {sorted(reels)}. Each custom-columns "
        "column is written TITLE:path, separated by commas without spaces.",
        fr=f"pods-colonnes.txt contient {lignes}, attendu une ligne d'en-tête à deux titres de "
        f"colonne, puis une ligne par Pod de web, le Pod puis son nœud : {sorted(reels)}. Chaque "
        "colonne de custom-columns s'écrit TITRE:chemin, séparées par des virgules sans espace.",
    )
