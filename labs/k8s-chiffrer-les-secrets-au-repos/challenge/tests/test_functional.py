"""test_functional.py : k8s-chiffrer-les-secrets-au-repos

Trois affirmations, lues là où elles se jouent : dans etcd pour le chiffrement,
auprès de l'API server pour les droits. Relire le manifeste ou la
configuration ne prouverait rien : un fichier présent mais jamais relu par
l'API server, ou une liste de fournisseurs où `identity` reste en premier,
laissent les Secrets en clair.

Aucune n'est vraie avant le travail : au départ, l'API server n'a aucun
chiffrement, cle-banque et cle-paie sont en clair dans etcd, et facturation lit
tous les Secrets de tresorerie.
"""

from __future__ import annotations

import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "tresorerie"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
ETCDCTL = (
    "etcdctl --endpoints=https://127.0.0.1:2379 "
    "--cacert=/etc/kubernetes/pki/etcd/ca.crt "
    "--cert=/etc/kubernetes/pki/etcd/server.crt "
    "--key=/etc/kubernetes/pki/etcd/server.key"
)
PREFIXE = "k8s:enc:secretbox:v1:"
VALEURS = {"cle-banque": "FR7630006000011234567890189", "cle-paie": "Paie-Kappa-2026"}
SA = "--as=system:serviceaccount:tresorerie:facturation"

# L'API server relit sa configuration de chiffrement par intervalles quand le
# rechargement automatique est actif. Budget borné, pour ne pas recaler un
# candidat dont la configuration vient d'être posée.
BUDGET_S = 90
PAS_S = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _debut_dans_etcd(host, nom: str) -> str:
    """Les premiers octets de la valeur stockée, lisibles."""
    res = host.run(
        f"sudo {ETCDCTL} get /registry/secrets/{NAMESPACE}/{nom} --print-value-only "
        "| head -c 40 | tr -c '[:print:]' '.'"
    )
    return res.stdout.strip()


def _valeur_en_clair_dans_etcd(host, nom: str, valeur: str) -> bool:
    res = host.run(
        f"sudo {ETCDCTL} get /registry/secrets/{NAMESPACE}/{nom} --print-value-only "
        f"| grep -a -c -- {valeur}"
    )
    return res.stdout.strip() not in ("", "0")


# ----------------------------------------------------------------------
# 1. Un Secret écrit maintenant est chiffré par secretbox dans etcd.
# ----------------------------------------------------------------------
def test_un_nouveau_secret_est_chiffre_par_secretbox(host):
    sonde = "sonde-chiffrement"
    debut = ""
    fin = time.monotonic() + BUDGET_S
    while True:
        host.run(f"sudo {KUBECTL} -n {NAMESPACE} delete secret {sonde} --ignore-not-found")
        cree = host.run(
            f"sudo {KUBECTL} -n {NAMESPACE} create secret generic {sonde} "
            "--from-literal=valeur=Sonde-Lambda-7"
        )
        debut = _debut_dans_etcd(host, sonde) if cree.rc == 0 else ""
        if debut.startswith(PREFIXE) or time.monotonic() > fin:
            break
        time.sleep(PAS_S)
    host.run(f"sudo {KUBECTL} -n {NAMESPACE} delete secret {sonde} --ignore-not-found")

    assert cree.rc == 0, message(
        en=f"Cannot create a Secret in {NAMESPACE}: {cree.stderr.strip()}. Is the "
        "API server running?",
        fr=f"Impossible de créer un Secret dans {NAMESPACE} : {cree.stderr.strip()}. "
        "L'API server tourne-t-il ?",
    )
    assert debut.startswith(PREFIXE), message(
        en=f"A Secret written now is stored in etcd as \"{debut}…\", without the "
        f"prefix {PREFIXE}. Either the API server does not read an "
        "encryption configuration, or secretbox is not the FIRST provider: only "
        "the first one encrypts new writes.",
        fr=f"Un Secret écrit maintenant est stocké dans etcd sous la forme "
        f"« {debut}… », sans le préfixe {PREFIXE}. Soit l'API server ne lit "
        "aucune configuration de chiffrement, soit secretbox n'est pas le "
        "PREMIER fournisseur : seul le premier chiffre les nouvelles écritures.",
    )


# ----------------------------------------------------------------------
# 2. Les Secrets déjà présents sont réécrits, et restent lisibles par l'API.
# ----------------------------------------------------------------------
def test_les_secrets_existants_sont_chiffres_et_restent_lisibles(host):
    for nom, valeur in VALEURS.items():
        debut = _debut_dans_etcd(host, nom)
        assert debut.startswith(PREFIXE) and not _valeur_en_clair_dans_etcd(host, nom, valeur), message(
            en=f"The Secret {nom}, created before encryption, is still stored as "
            f"\"{debut}…\" in etcd. Changing the configuration only affects NEW "
            "writes: the Secrets already there must be rewritten.",
            fr=f"Le Secret {nom}, créé avant le chiffrement, est toujours stocké "
            f"sous la forme « {debut}… » dans etcd. Changer la configuration ne "
            "touche que les NOUVELLES écritures : les Secrets déjà présents "
            "doivent être réécrits.",
        )
        lu = host.run(
            f"sudo {KUBECTL} -n {NAMESPACE} get secret {nom} "
            "-o jsonpath='{.data}' | tr -d '{}\"' | cut -d: -f2 | base64 -d"
        )
        assert lu.stdout.strip() == valeur, message(
            en=f"Through the API, {nom} no longer gives back its value (read: "
            f"\"{lu.stdout.strip()}\"). The API server must still decrypt it: did "
            "the key change after the rewrite?",
            fr=f"Par l'API, {nom} ne rend plus sa valeur (lu : "
            f"« {lu.stdout.strip()} »). L'API server doit toujours le déchiffrer : "
            "la clé a-t-elle changé après la réécriture ?",
        )


# ----------------------------------------------------------------------
# 3. facturation ne lit que cle-banque.
# ----------------------------------------------------------------------
def test_facturation_ne_lit_que_cle_banque(host):
    def peut(verbe_objet: str) -> str:
        return host.run(
            f"sudo {KUBECTL} auth can-i {verbe_objet} -n {NAMESPACE} {SA}"
        ).stdout.strip()

    autres = {
        "get secret/cle-paie": peut("get secret/cle-paie"),
        "list secrets": peut("list secrets"),
        "watch secrets": peut("watch secrets"),
    }
    trop = [k for k, v in autres.items() if v == "yes"]
    assert not trop, message(
        en=f"The ServiceAccount facturation can still do: {', '.join(trop)}. It "
        "only needs cle-banque. Remember that list and watch return the CONTENT "
        "of every Secret, not just their names.",
        fr=f"Le ServiceAccount facturation peut encore : {', '.join(trop)}. Il "
        "n'a besoin que de cle-banque. Rappel : list et watch rendent le "
        "CONTENU de tous les Secrets, pas seulement leurs noms.",
    )
    assert peut("get secret/cle-banque") == "yes", message(
        en="The ServiceAccount facturation can no longer read cle-banque, which "
        "it needs. Restrict its rights without removing this one.",
        fr="Le ServiceAccount facturation ne peut plus lire cle-banque, dont il "
        "a besoin. Restreignez ses droits sans retirer celui-là.",
    )
