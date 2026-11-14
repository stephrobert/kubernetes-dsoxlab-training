"""test_functional.py : kubeadm-verifier-et-renouveler-les-certificats

1. ~/pki/reponses.yaml donne l'échéance de la CA du cluster, lue dans son
   certificat au moment du check ;
2. les sept certificats du plan de contrôle portent un autre numéro de série
   que celui relevé par le setup ;
3. le kubeconfig de kube-controller-manager et de kube-scheduler porte un
   nouveau certificat client, et les deux ont redémarré après sa réécriture (l'API server et etcd, eux, rechargent
   seuls leur certificat de service : mesuré sur 1.37) ;
4. le kubeconfig de l'utilisateur porte le certificat client renouvelé
   d'admin.conf, et kubectl répond avec lui.

Les quatre échouent sur l'état de départ : réponse vide, numéros de série
inchangés.
"""

from __future__ import annotations

import base64
import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

CERTS = ['apiserver', 'apiserver-kubelet-client', 'apiserver-etcd-client', 'front-proxy-client', 'etcd/server', 'etcd/peer', 'etcd/healthcheck-client']


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _maison(host) -> str:
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _releve(host) -> dict:
    res = host.run("sudo cat /var/lib/dsoxlab/pki-series.json")
    assert res.rc == 0, message(
        en="The serial numbers recorded by the setup are missing: run the lab again with dsoxlab run.",
        fr="Les numéros de série relevés par le setup sont absents : rejouez le lab avec dsoxlab run.",
    )
    return json.loads(res.stdout)


def _serie_fichier(host, chemin: str) -> str:
    return host.check_output(f"sudo openssl x509 -noout -serial -in {chemin}").split("=", 1)[1].strip()


def _serie_pem(host, pem: str) -> str:
    res = host.run(f"echo '{base64.b64encode(pem.encode()).decode()}' | base64 -d | openssl x509 -noout -serial")
    return res.stdout.split("=", 1)[1].strip() if res.rc == 0 and "=" in res.stdout else ""


def test_l_echeance_de_la_ca_est_la_bonne(host):
    fin = host.check_output("sudo openssl x509 -noout -enddate -in /etc/kubernetes/pki/ca.crt").split("=", 1)[1]
    attendue = host.check_output(f"date -u -d '{fin}' +%Y-%m-%d").strip()
    fichier = host.file(f"{_maison(host)}/pki/reponses.yaml")
    donnee = str((yaml.safe_load(fichier.content_string) or {}).get("ca_expire_le") or "").strip() if fichier.exists else ""
    assert donnee == attendue, message(
        en=f"ca_expire_le is {donnee!r}; it is not the expiry date of the cluster's certificate authority.",
        fr=f"ca_expire_le vaut {donnee!r} ; ce n'est pas la date d'échéance de l'autorité de certification du "
        "cluster.",
    )


def test_les_certificats_du_plan_de_controle_sont_renouveles(host):
    releve = _releve(host)
    inchanges = [nom for nom in CERTS if _serie_fichier(host, f"/etc/kubernetes/pki/{nom}.crt") == releve.get(nom)]
    assert not inchanges, message(
        en=f"These control plane certificates have not been renewed: {inchanges}.",
        fr=f"Ces certificats du plan de contrôle n'ont pas été renouvelés : {inchanges}.",
    )


def _date_fichier(host, chemin: str) -> int:
    return int(host.check_output(f"sudo stat -c %Y {chemin}").strip())


def _demarrage_conteneur(host, nom: str) -> int | None:
    """L'heure de création du conteneur en marche, en secondes depuis l'époque."""
    res = host.run(f"sudo crictl ps --name '^{nom}$' -o json")
    if res.rc != 0:
        return None
    conteneurs = json.loads(res.stdout).get("containers") or []
    return int(conteneurs[0]["createdAt"]) // 10**9 if conteneurs else None


def test_le_controller_manager_et_le_scheduler_ont_redemarre(host):
    # kube-apiserver et etcd rechargent seuls leur certificat de service quand
    # le fichier change (mesuré sur 1.37). kube-controller-manager et
    # kube-scheduler, eux, ne relisent le certificat client de leur kubeconfig
    # qu'au démarrage : sans redémarrage, ils tomberont à l'échéance de l'ancien.
    # Le kubeconfig doit avoir été réécrit pendant le lab (après le relevé du
    # setup), et le conteneur avoir démarré APRÈS cette réécriture.
    # La date seule ne suffit pas : un touch la change. Le numéro de série du
    # certificat client porté par le kubeconfig doit lui aussi avoir changé.
    releve = _releve(host)
    depart = _date_fichier(host, "/var/lib/dsoxlab/pki-series.json")
    ecarts = {}
    for nom, conf in (("kube-controller-manager", "controller-manager.conf"),
                      ("kube-scheduler", "scheduler.conf")):
        assert conf in releve, message(
            en="The serial numbers recorded by the setup predate this version of the lab: run it again with "
            "dsoxlab run.",
            fr="Les numéros de série relevés par le setup datent d'une version antérieure du lab : rejouez-le "
            "avec dsoxlab run.",
        )
        contenu = yaml.safe_load(host.check_output(f"sudo cat /etc/kubernetes/{conf}")) or {}
        donnees = ((contenu.get("users") or [{}])[0].get("user") or {}).get("client-certificate-data", "")
        serie = _serie_pem(host, base64.b64decode(donnees).decode()) if donnees else ""
        ecrit = _date_fichier(host, f"/etc/kubernetes/{conf}")
        demarre = _demarrage_conteneur(host, nom)
        if ecrit <= depart or serie in ("", releve[conf]):
            ecarts[nom] = message(en=f"{conf} has not been renewed", fr=f"{conf} n'a pas été renouvelé")
        elif demarre is None or demarre <= ecrit:
            ecarts[nom] = message(en=f"still runs with the client certificate read before the renewal of {conf}",
                                  fr=f"tourne encore avec le certificat client lu avant le renouvellement de {conf}")
    assert not ecarts, message(
        en=f"These components still use their old client certificate: {ecarts}. They only read their kubeconfig "
        "when they start.",
        fr=f"Ces composants utilisent encore leur ancien certificat client : {ecarts}. Ils ne lisent leur "
        "kubeconfig qu'au démarrage.",
    )


def test_le_kubeconfig_porte_le_nouveau_certificat_et_kubectl_repond(host):
    releve = _releve(host)
    admin = yaml.safe_load(host.check_output("sudo cat /etc/kubernetes/admin.conf"))
    serie_admin = _serie_pem(host, base64.b64decode(admin["users"][0]["user"]["client-certificate-data"]).decode())
    conf = host.run(f"sudo cat {_maison(host)}/.kube/config")
    utilisateur = yaml.safe_load(conf.stdout) if conf.rc == 0 else {}
    donnees = ((utilisateur.get("users") or [{}])[0].get("user") or {}).get("client-certificate-data", "")
    serie_utilisateur = _serie_pem(host, base64.b64decode(donnees).decode()) if donnees else ""
    repond = host.run('sudo -u "${SUDO_USER:-ansible}" kubectl --kubeconfig '
                      f"{_maison(host)}/.kube/config get nodes").rc == 0
    assert serie_admin != releve.get("admin.conf") and serie_utilisateur == serie_admin and repond, message(
        en="The user's kubeconfig does not carry the renewed admin certificate, or kubectl does not answer with it. "
        "admin.conf is renewed with the others, then copied again to ~/.kube/config.",
        fr="Le kubeconfig de l'utilisateur ne porte pas le certificat d'administration renouvelé, ou kubectl ne "
        "répond pas avec lui. admin.conf se renouvelle avec les autres, puis se recopie dans ~/.kube/config.",
    )
