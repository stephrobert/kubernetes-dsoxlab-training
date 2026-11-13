"""test_functional.py : kubeadm-verifier-et-renouveler-les-certificats

1. ~/pki/reponses.yaml donne l'échéance de la CA du cluster, lue dans son
   certificat au moment du check ;
2. les sept certificats du plan de contrôle portent un autre numéro de série
   que celui relevé par le setup ;
3. l'API server (6443) et etcd (2379) servent le certificat du disque : un
   renouvellement non rechargé ne passe pas ;
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


def _serie_servie(host, port: int) -> str:
    res = host.run(f"echo | openssl s_client -connect 127.0.0.1:{port} 2>/dev/null | openssl x509 -noout -serial")
    return res.stdout.split("=", 1)[1].strip() if res.rc == 0 and "=" in res.stdout else ""


def test_l_api_server_et_etcd_servent_les_nouveaux_certificats(host):
    ecarts = {}
    for port, nom in ((6443, "apiserver"), (2379, "etcd/server")):
        servi, disque = _serie_servie(host, port), _serie_fichier(host, f"/etc/kubernetes/pki/{nom}.crt")
        if servi != disque:
            ecarts[nom] = message(en=f"serves {servi or 'nothing'}, disk has {disque}",
                                  fr=f"sert {servi or 'rien'}, le disque porte {disque}")
    assert not ecarts, message(
        en=f"These components do not serve the certificate on disk: {ecarts}. A renewed certificate is only "
        "used once the component has been restarted.",
        fr=f"Ces composants ne servent pas le certificat du disque : {ecarts}. Un certificat renouvelé ne sert "
        "qu'une fois le composant redémarré.",
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
