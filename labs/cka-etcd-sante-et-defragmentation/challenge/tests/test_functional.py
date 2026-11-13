"""test_functional.py : cka-etcd-sante-et-defragmentation

Chaque test compare une réponse de ~/etcd/reponses.yaml à ce qu'etcd dit de
lui-même au moment du check, ou mesure la base elle-même. Les valeurs réelles
sont lues avec etcdctl, dans le Pod etcd, avec ses certificats.

La défragmentation se juge sur la taille : la base doit avoir rendu au moins la
moitié de la taille relevée après le gonflement du setup, et l'espace qu'elle
occupe doit être, pour l'essentiel, de l'espace utilisé. Un compactage seul
libère la place DANS le fichier sans le réduire, et ne passe pas.

Les trois échouent sur l'état de départ : réponses vides, base gonflée.
"""

from __future__ import annotations

import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-cp.lab"
ETCDCTL = (f"{KUBECTL} -n kube-system exec etcd-{NOEUD} -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt "
           "--cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key")
QUOTA_PAR_DEFAUT = 2 * 1024**3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(NOEUD))


def _reponses(host) -> dict:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    fichier = host.file(f"{maison}/etcd/reponses.yaml")
    assert fichier.exists, message(en="~/etcd/reponses.yaml is missing.", fr="~/etcd/reponses.yaml est absent.")
    try:
        return yaml.safe_load(fichier.content_string) or {}
    except yaml.YAMLError as erreur:
        pytest.fail(message(en=f"reponses.yaml is not valid YAML: {erreur}",
                            fr=f"reponses.yaml n'est pas du YAML valide : {erreur}"))


def _statut(host) -> dict:
    return json.loads(host.check_output(f"{ETCDCTL} endpoint status -w json"))[0]["Status"]


def test_le_membre_et_sa_sante_sont_ceux_d_etcd(host):
    membres = json.loads(host.check_output(f"{ETCDCTL} member list -w json"))["members"]
    vrais = {format(m["ID"], "x"): m.get("clientURLs") or [] for m in membres}
    reponses = _reponses(host)
    donne = str(reponses.get("member_id") or "").strip().lower().removeprefix("0x")
    point = str(reponses.get("endpoint") or "").strip()
    sante = host.run(f"{ETCDCTL} endpoint health").rc == 0
    assert donne in vrais and point in vrais[donne] and reponses.get("healthy") is sante is True, message(
        en=f"member_id {donne!r}, endpoint {point!r}, healthy {reponses.get('healthy')!r}: they do not match "
        "what member list and endpoint health say of the etcd member.",
        fr=f"member_id {donne!r}, endpoint {point!r}, healthy {reponses.get('healthy')!r} : ils ne "
        "correspondent pas à ce que member list et endpoint health disent du membre etcd.",
    )


def test_le_quota_est_celui_qu_etcd_applique(host):
    commande = " ".join(json.loads(host.check_output(f"{KUBECTL} -n kube-system get pod etcd-{NOEUD} -o json"))
                        ["spec"]["containers"][0].get("command") or [])
    attendu = QUOTA_PAR_DEFAUT
    for mot in commande.split():
        if mot.startswith("--quota-backend-bytes="):
            attendu = int(mot.split("=", 1)[1])
    donne = _reponses(host).get("quota_bytes")
    assert isinstance(donne, int) and donne == attendu, message(
        en=f"quota_bytes is {donne!r}; it is not the space quota this etcd applies (its option, or the "
        "default when it sets none).",
        fr=f"quota_bytes vaut {donne!r} ; ce n'est pas le quota d'espace qu'applique cet etcd (son option, ou "
        "la valeur par défaut s'il n'en pose aucune).",
    )


def test_la_base_a_ete_defragmentee(host):
    avant = host.run("sudo cat /var/lib/dsoxlab/etcd-taille-avant").stdout.strip()
    assert avant.isdigit(), message(
        en="The size recorded by the setup is missing: run the lab again with dsoxlab run.",
        fr="La taille relevée par le setup est absente : rejouez le lab avec dsoxlab run.",
    )
    statut = _statut(host)
    taille, utilisee = statut["dbSize"], statut["dbSizeInUse"]
    assert taille <= int(avant) // 2 and utilisee >= taille * 0.6, message(
        en=f"The etcd database weighs {taille // 2**20} MiB, of which {utilisee // 2**20} MiB in use "
        f"(after the setup: {int(avant) // 2**20} MiB). It has not given back the freed space: compaction "
        "frees it inside the file, defragmentation gives it back.",
        fr=f"La base etcd pèse {taille // 2**20} Mio, dont {utilisee // 2**20} Mio utilisés (après le setup : "
        f"{int(avant) // 2**20} Mio). Elle n'a pas rendu la place libérée : le compactage la libère dans le "
        "fichier, la défragmentation la rend.",
    )
