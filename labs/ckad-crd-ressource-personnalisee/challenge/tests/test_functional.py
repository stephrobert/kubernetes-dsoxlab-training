"""test_functional.py : ckad-crd-ressource-personnalisee

Ces tests lisent l'état du cluster « lab », les ressources Sauvegarde et ce que
l'apprenant a consigné dans ~/sauvegardes/. Un test vérifie un seul état.

Tous échouent avant le travail : quotidienne n'existe pas, hebdomadaire garde
14 jours, ~/sauvegardes/ est vide et ancienne reste en Terminating. Aucun test
n'attend : une ressource personnalisée sans contrôleur ne change pas d'état
toute seule.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "sauvegardes"
CRD = "sauvegardes.atelier.formation.k8s"
API = "atelier.formation.k8s/v1"
MEMOIRE = "/var/lib/dsoxlab/crd-ressource-personnalisee.json"
HORS_BORNES = re.compile(r"less than or equal to 365|inférieur ou égal à 365", re.IGNORECASE)


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


def _memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the initial state is missing: run dsoxlab reset ckad-crd-ressource-personnalisee.",
            fr="La mémoire de l'état initial est absente : lancez dsoxlab reset ckad-crd-ressource-personnalisee.",
        ))
    return json.loads(res.stdout)


def _consigne(host, nom: str) -> str:
    f = host.file(f"{_maison(host)}/sauvegardes/{nom}")
    return f.content_string if f.exists else ""


# ----------------------------------------------------------------------
# 1. La ressource quotidienne existe avec les valeurs demandées.
# ----------------------------------------------------------------------
def test_la_sauvegarde_quotidienne_existe_avec_les_valeurs_demandees(host):
    r = _json(host, f"-n {NS} get sauvegardes.atelier.formation.k8s quotidienne")
    assert r is not None, message(
        en=f"No Sauvegarde quotidienne in {NS}.", fr=f"Aucune Sauvegarde quotidienne dans {NS}.",
    )
    spec = r.get("spec") or {}
    assert spec.get("source") == "donnees-registre" and spec.get("retentionJours") == 7, message(
        en=f"quotidienne saves {spec.get('source')!r} for {spec.get('retentionJours')!r} day(s). Expected "
        "donnees-registre, kept 7 days.",
        fr=f"quotidienne sauvegarde {spec.get('source')!r} pendant {spec.get('retentionJours')!r} jour(s). "
        "Attendu donnees-registre, gardée 7 jours.",
    )


# ----------------------------------------------------------------------
# 2. hebdomadaire est modifiée, sans avoir été recréée.
# ----------------------------------------------------------------------
def test_hebdomadaire_garde_trente_jours_sans_avoir_ete_recreee(host):
    memoire = _memoire(host)
    r = _json(host, f"-n {NS} get sauvegardes.atelier.formation.k8s hebdomadaire")
    assert r is not None, message(
        en=f"No Sauvegarde hebdomadaire in {NS}: it was to be modified, not deleted.",
        fr=f"Aucune Sauvegarde hebdomadaire dans {NS} : elle devait être modifiée, pas supprimée.",
    )
    meme = r["metadata"]["uid"] == memoire["hebdomadaire_uid"]
    jours = (r.get("spec") or {}).get("retentionJours")
    identite_en = "is" if meme else "is no longer"
    identite_fr = "est" if meme else "n'est plus"
    assert meme and jours == 30, message(
        en=f"hebdomadaire keeps {jours!r} day(s), and {identite_en} the resource of the start. Expected 30 days, "
        "on the same resource.",
        fr=f"hebdomadaire garde {jours!r} jour(s), et {identite_fr} la ressource du départ. Attendu 30 jours, "
        "sur la même ressource.",
    )


# ----------------------------------------------------------------------
# 3. Le groupe et la version de l'API de Sauvegarde sont consignés.
# ----------------------------------------------------------------------
def test_le_groupe_et_la_version_de_l_api_sont_consignes(host):
    contenu = _consigne(host, "api.txt")
    assert API in contenu, message(
        en="~/sauvegardes/api.txt does not give the API group and version that serve the kind Sauvegarde, in "
        "the form group/version.",
        fr="~/sauvegardes/api.txt ne donne pas le groupe et la version d'API qui servent le kind Sauvegarde, "
        "sous la forme groupe/version.",
    )


# ----------------------------------------------------------------------
# 4. L'API refuse une rétention hors bornes, et son refus est consigné.
# ----------------------------------------------------------------------
def test_le_refus_d_une_retention_hors_bornes_est_consigne(host):
    contenu = _consigne(host, "refus.txt")
    assert HORS_BORNES.search(contenu), message(
        en="~/sauvegardes/refus.txt does not hold the message by which the API refuses a Sauvegarde kept "
        "beyond the allowed maximum.",
        fr="~/sauvegardes/refus.txt ne contient pas le message par lequel l'API refuse une Sauvegarde gardée "
        "au-delà du maximum permis.",
    )
    essai = (
        f"printf '%s' '{{\"apiVersion\":\"{API}\",\"kind\":\"Sauvegarde\",\"metadata\":{{\"name\":\"essai-borne\","
        f"\"namespace\":\"{NS}\"}},\"spec\":{{\"source\":\"x\",\"retentionJours\":400}}}}' "
        f"| {ADMIN} apply --dry-run=server -f -"
    )
    res = host.run(essai)
    assert res.rc != 0 and HORS_BORNES.search(res.stderr), message(
        en="The API now accepts a Sauvegarde kept 400 days: the bounds of the schema no longer hold.",
        fr="L'API accepte désormais une Sauvegarde gardée 400 jours : les bornes du schéma ne tiennent plus.",
    )


# ----------------------------------------------------------------------
# 5. ancienne n'est plus bloquée, et la CRD est celle du départ.
# ----------------------------------------------------------------------
def test_ancienne_est_debloquee_sans_toucher_a_la_crd(host):
    memoire = _memoire(host)
    ancienne = _json(host, f"-n {NS} get sauvegardes.atelier.formation.k8s ancienne")
    crd = _json(host, f"get crd {CRD}")
    meme_crd = crd is not None and crd["metadata"]["uid"] == memoire["crd_uid"]
    assert ancienne is None and meme_crd, message(
        en=f"ancienne {'still exists' if ancienne else 'is gone'}, and the CRD "
        f"{'is the one of the start' if meme_crd else 'was deleted or recreated'}. Expected ancienne gone, "
        "without the CRD and the other resources having been deleted.",
        fr=f"ancienne {'existe encore' if ancienne else 'a disparu'}, et la CRD "
        f"{'est celle du départ' if meme_crd else 'a été supprimée ou recréée'}. Attendu ancienne disparue, "
        "sans que la CRD et les autres ressources aient été supprimées.",
    )
