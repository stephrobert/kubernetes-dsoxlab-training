"""test_functional.py : k8s-labels-et-selecteurs

Ces tests lisent l'état du cluster et le relevé ~/etiquettes/releve.txt. Un
test vérifie un seul état demandé par l'énoncé.

Le label est jugé dans le MODÈLE de Pod du Deployment web : c'est ce qui le
fait survivre au remplacement des Pods. Un label posé à la main sur les Pods
ne compte pas. L'annotation est cherchée parmi les annotations du Deployment,
pas parmi ses labels. Le sélecteur consigné est rejoué tel quel par
kubectl get pods -l, et doit rendre exactement les Pods de api, avec une
négation (!= ou !clé) : `app=api` les rend aussi, mais n'est pas le geste
demandé.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "etiquettes"
RELEVE = f"~/{NS}/releve.txt"
#: Ce qu'un sélecteur de labels peut contenir, rien de plus : il est passé au
#: shell de la cible entre apostrophes.
SELECTEUR_LICITE = re.compile(r"^[A-Za-z0-9=!,()._/ -]+$")
ATTENTE = 60
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
    res = host.run(f"{ADMIN} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _web(host) -> dict:
    dep = _json(host, "get deployment web")
    assert dep is not None, message(
        en=f"No Deployment web in {NS}: run dsoxlab reset k8s-labels-et-selecteurs.",
        fr=f"Aucun Deployment web dans {NS} : lancez dsoxlab reset k8s-labels-et-selecteurs.",
    )
    return dep


def _pods_vivants(host, selecteur: str) -> set[str]:
    """Les Pods que rend un sélecteur, hors Pods en cours de suppression : un
    rollout laisse quelques instants des Pods de l'ancien modèle."""
    pods = (_json(host, f"get pods -l '{selecteur}'") or {}).get("items") or []
    return {p["metadata"]["name"] for p in pods if not p["metadata"].get("deletionTimestamp")}


# ----------------------------------------------------------------------
# 1. env=prod dans le modèle de Pod de web.
# ----------------------------------------------------------------------
def test_env_prod_est_dans_le_modele_de_pod_de_web(host):
    dep = _web(host)
    modele = (dep["spec"]["template"]["metadata"].get("labels") or {})
    assert modele.get("env") == "prod", message(
        en=f"The Pod template of web carries the labels {modele}, without env=prod. A label "
        "put on the Pods by hand disappears with them when they are replaced: a lasting label "
        "is written in spec.template.metadata.labels. Reread the section of the lesson on a "
        "manual label that does not last.",
        fr=f"Le modèle de Pod de web porte les labels {modele}, sans env=prod. Un label posé à "
        "la main sur les Pods disparaît avec eux quand ils sont remplacés : un label durable "
        "s'écrit dans spec.template.metadata.labels. Relisez la section de la leçon sur le "
        "label manuel qui ne dure pas.",
    )
    # Le modèle est juste : on laisse le rollout remplacer les Pods.
    selecteur = ",".join(f"{k}={v}" for k, v in sorted(
        (dep["spec"]["selector"].get("matchLabels") or {}).items()))
    fin = time.monotonic() + ATTENTE
    while True:
        tous = _pods_vivants(host, selecteur)
        sans = tous - _pods_vivants(host, f"{selecteur},env=prod")
        dep = _web(host)
        fini = (dep.get("status") or {}).get("updatedReplicas") == dep["spec"].get("replicas")
        if (fini and not sans) or time.monotonic() >= fin:
            break
        time.sleep(PAS)
    assert tous and not sans, message(
        en=f"After {ATTENTE}s, Pods of web still lack env=prod: {sorted(sans)}.",
        fr=f"Après {ATTENTE}s, des Pods de web n'ont toujours pas env=prod : {sorted(sans)}.",
    )


# ----------------------------------------------------------------------
# 2. Une annotation description sur web.
# ----------------------------------------------------------------------
def test_une_annotation_description_est_posee_sur_web(host):
    dep = _web(host)
    annotations = dep["metadata"].get("annotations") or {}
    description = annotations.get("description", "").strip()
    assert description, message(
        en="The Deployment web has no annotation description. A description is not used to "
        "select: it is an annotation, not a label, put on the Deployment itself. Reread the "
        "section of the lesson on annotations.",
        fr="Le Deployment web n'a pas d'annotation description. Une description ne sert pas à "
        "sélectionner : c'est une annotation, pas un label, posée sur le Deployment lui-même. "
        "Relisez la section de la leçon sur les annotations.",
    )


# ----------------------------------------------------------------------
# 3. Un sélecteur à négation qui rend exactement les Pods de api.
# ----------------------------------------------------------------------
def test_le_selecteur_consigne_rend_exactement_les_pods_de_api(host, releve):
    brut = releve.get("selecteur", "").strip().strip("'\"")
    assert brut, message(
        en=f"The key 'selecteur' of {RELEVE} has no value.",
        fr=f"La clé 'selecteur' de {RELEVE} n'a pas de valeur.",
    )
    assert SELECTEUR_LICITE.match(brut), message(
        en=f"selecteur is {brut!r}: write only the selector, as passed after -l.",
        fr=f"selecteur vaut {brut!r} : écrivez seulement le sélecteur, tel qu'il suit -l.",
    )
    assert "!" in brut, message(
        en=f"selecteur is {brut!r}, without a negation. The request is to select by what the "
        "Pods do NOT carry: != or !key. Reread the section of the lesson on selectors.",
        fr=f"selecteur vaut {brut!r}, sans négation. La demande est de sélectionner par ce que "
        "les Pods ne portent PAS : != ou !clé. Relisez la section de la leçon sur les "
        "sélecteurs.",
    )
    rendus = _pods_vivants(host, brut)
    attendus = _pods_vivants(host, "app=api")
    assert attendus and rendus == attendus, message(
        en=f"kubectl get pods -l '{brut}' returns {sorted(rendus)}, expected exactly the Pods "
        f"of api {sorted(attendus)}. A != also keeps the objects that do not have the key at "
        "all: check what your selector returns before writing it down.",
        fr=f"kubectl get pods -l '{brut}' rend {sorted(rendus)}, attendu exactement les Pods "
        f"de api {sorted(attendus)}. Un != retient aussi les objets qui n'ont pas du tout la "
        "clé : vérifiez ce que rend votre sélecteur avant de le consigner.",
    )
