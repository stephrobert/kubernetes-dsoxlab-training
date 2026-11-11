"""test_functional.py : k8s-creer-ou-appliquer

Ces tests lisent le namespace livraisons du cluster « lab » et le dossier
~/livraisons/appli/ : les annotations last-applied-configuration, ce qu'un
nouvel apply du fichier de suivi ferait (le serveur le calcule en
--dry-run=server, sans rien changer), les field managers de tarifs, et ce que
--prune a retiré ou épargné. Un test vérifie un seul état demandé par l'énoncé.

Tous échouent avant le travail : le Service et la ConfigMap du dossier
n'existent pas, suivi.yaml fixe encore replicas, l'image de tarifs n'a pas de
gestionnaire nommé, et suivi-ancien existe.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "livraisons"
MEMOIRE = "/var/lib/dsoxlab/creer-ou-appliquer.json"
V2 = "nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
GESTIONNAIRE = "equipe-tarifs"
AUTOSCALER = 4
DERNIER = "kubectl.kubernetes.io/last-applied-configuration"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Le dossier entier est appliqué, sous-dossiers compris.
# ----------------------------------------------------------------------
def test_le_dossier_est_applique_sous_dossiers_compris(host):
    manquants = []
    for objet in ("service/suivi", "configmap/suivi-config"):
        o = _json(host, f"-n {NS} get {objet}")
        if o is None or DERNIER not in (o["metadata"].get("annotations") or {}):
            manquants.append(objet)
    assert not manquants, message(
        en=f"These objects of ~/{NS}/appli/ were not applied from the folder: {manquants}. They "
        "live in subfolders, and an object created otherwise than by apply carries no "
        "last-applied-configuration annotation.",
        fr=f"Ces objets de ~/{NS}/appli/ n'ont pas été appliqués depuis le dossier : {manquants}. Ils "
        "vivent dans des sous-dossiers, et un objet créé autrement que par apply ne porte pas "
        "l'annotation last-applied-configuration.",
    )


# ----------------------------------------------------------------------
# 2. Un nouvel apply de suivi.yaml laisse le nombre choisi par l'autoscaler.
# ----------------------------------------------------------------------
def test_reappliquer_suivi_laisse_les_replicas_de_l_autoscaler(host):
    fichier = f"{_maison(host)}/{NS}/appli/suivi.yaml"
    f = host.file(fichier)
    assert f.exists, message(
        en=f"~/{NS}/appli/suivi.yaml no longer exists: it is the versioned description of suivi.",
        fr=f"~/{NS}/appli/suivi.yaml n'existe plus : c'est la description versionnée de suivi.",
    )
    doc = next((d for d in yaml.safe_load_all(f.content_string) if isinstance(d, dict)), {}) or {}
    fixe = "replicas" in (doc.get("spec") or {})
    vivant = (_json(host, f"-n {NS} get deployment suivi") or {}).get("spec", {}).get("replicas")
    simule = _json(host, f"apply --dry-run=server -f {fichier}")
    apres = None if simule is None else simule.get("spec", {}).get("replicas")
    assert not fixe and vivant == AUTOSCALER and apres == AUTOSCALER, message(
        en=f"suivi.yaml {'still sets' if fixe else 'no longer sets'} replicas; suivi runs {vivant} "
        f"replica(s), and applying the file again would leave {apres}. Expected: a file without "
        f"replicas, and {AUTOSCALER} replicas kept by a new apply, the number chosen by the "
        "autoscaler. Removing the field from the file is not always enough.",
        fr=f"suivi.yaml {'fixe encore' if fixe else 'ne fixe plus'} replicas ; suivi tourne avec "
        f"{vivant} réplica(s), et réappliquer le fichier en laisserait {apres}. Attendu : un fichier "
        f"sans replicas, et {AUTOSCALER} réplicas conservés par un nouvel apply, le nombre choisi "
        "par l'autoscaler. Retirer le champ du fichier ne suffit pas toujours.",
    )


# ----------------------------------------------------------------------
# 3. L'image de tarifs appartient au gestionnaire nommé, par server-side apply.
# ----------------------------------------------------------------------
def test_l_image_de_tarifs_appartient_au_gestionnaire_equipe_tarifs(host):
    d = _json(host, f"-n {NS} get deployment tarifs --show-managed-fields")
    assert d is not None, message(
        en="The tarifs Deployment no longer exists.",
        fr="Le Deployment tarifs n'existe plus.",
    )
    image = d["spec"]["template"]["spec"]["containers"][0].get("image")
    possede = any(
        m.get("manager") == GESTIONNAIRE and m.get("operation") == "Apply"
        and '"f:image"' in json.dumps(m.get("fieldsV1") or {})
        for m in d["metadata"].get("managedFields") or []
    )
    gestionnaires = sorted({f"{m.get('manager')}/{m.get('operation')}"
                            for m in d["metadata"].get("managedFields") or []})
    assert image == V2 and possede, message(
        en=f"tarifs runs {image!r}, and its field managers are {gestionnaires}. Expected version 2, "
        f"with the image owned by the {GESTIONNAIRE} manager through a server-side apply.",
        fr=f"tarifs tourne en {image!r}, et ses gestionnaires de champs sont {gestionnaires}. Attendu "
        f"la version 2, avec l'image possédée par le gestionnaire {GESTIONNAIRE} au moyen d'un "
        "server-side apply.",
    )


# ----------------------------------------------------------------------
# 4. --prune a retiré l'objet sorti du dossier, et lui seul.
# ----------------------------------------------------------------------
def test_prune_retire_suivi_ancien_et_epargne_journal(host):
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset k8s-creer-ou-appliquer.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset k8s-creer-ou-appliquer.",
        ))
    ancien = _json(host, f"-n {NS} get configmap suivi-ancien")
    journal = _json(host, f"-n {NS} get configmap journal")
    intact = journal is not None and journal["metadata"]["uid"] == json.loads(res.stdout)["journal_uid"]
    assert ancien is None and intact, message(
        en=f"suivi-ancien {'still exists' if ancien else 'is gone'} and journal "
        f"{'is intact' if intact else 'was deleted or recreated'}. Expected: the object whose file "
        "left the folder is gone, and the object that never belonged to the folder survives.",
        fr=f"suivi-ancien {'existe encore' if ancien else 'a disparu'} et journal "
        f"{'est intact' if intact else 'a été supprimé ou recréé'}. Attendu : l'objet dont le fichier "
        "a quitté le dossier a disparu, et l'objet qui n'a jamais appartenu au dossier survit.",
    )
