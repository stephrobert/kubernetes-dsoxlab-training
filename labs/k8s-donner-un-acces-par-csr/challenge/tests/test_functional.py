"""test_functional.py : k8s-donner-un-acces-par-csr

1. la demande camille est approuvée et délivrée, par le signataire des clients
   de l'API server, pour l'authentification d'un client, au nom de camille ;
2. ~/acces/camille.kubeconfig porte EXACTEMENT le certificat que l'API a
   délivré pour cette demande, et l'API l'identifie comme camille : un
   certificat signé à la main avec la clé de la CA du nœud ne passe pas ;
3. avec ce kubeconfig, camille lit les Pods d'equipe-web ;
4. et rien de plus : ni modifier, ni lire un Secret, ni regarder ailleurs.

Les quatre échouent sur l'état de départ : aucune demande, aucun kubeconfig.
"""

from __future__ import annotations

import base64
import json

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS = "equipe-web"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _maison(host) -> str:
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _demande(host) -> dict:
    res = host.run(f"{KUBECTL} get csr camille -o json")
    assert res.rc == 0, message(en="No CertificateSigningRequest named camille.",
                                fr="Aucune CertificateSigningRequest nommée camille.")
    return json.loads(res.stdout)


def _kubeconfig(host) -> str:
    chemin = f"{_maison(host)}/acces/camille.kubeconfig"
    assert host.file(chemin).exists, message(en="~/acces/camille.kubeconfig is missing.",
                                             fr="~/acces/camille.kubeconfig est absent.")
    return chemin


def _comme_camille(host, args: str):
    return host.run(f"sudo kubectl --kubeconfig {_kubeconfig(host)} {args}")


def test_la_demande_camille_est_approuvee_et_delivree(host):
    d = _demande(host)
    conditions = {c["type"]: c.get("status") for c in (d.get("status") or {}).get("conditions") or []}
    sujet = host.run(f"echo '{d['spec']['request']}' | base64 -d | openssl req -noout -subject").stdout
    ok = (d["spec"].get("signerName") == "kubernetes.io/kube-apiserver-client"
          and "client auth" in (d["spec"].get("usages") or [])
          and conditions.get("Approved") == "True" and (d.get("status") or {}).get("certificate")
          and "CN=camille" in sujet.replace(" ", ""))
    assert ok, message(
        en=f"The request camille is not as expected: signer {d['spec'].get('signerName')}, usages "
        f"{d['spec'].get('usages')}, conditions {conditions}, subject {sujet.strip()!r}. Expected the API server "
        "client signer, client auth, approved and issued, for CN=camille.",
        fr=f"La demande camille n'est pas conforme : signataire {d['spec'].get('signerName')}, usages "
        f"{d['spec'].get('usages')}, conditions {conditions}, sujet {sujet.strip()!r}. Attendu le signataire des "
        "clients de l'API server, client auth, approuvée et délivrée, pour CN=camille.",
    )


def test_le_kubeconfig_porte_le_certificat_delivre_et_l_identifie(host):
    delivre = base64.b64decode((_demande(host).get("status") or {}).get("certificate") or "")
    conf = yaml.safe_load(host.check_output(f"sudo cat {_kubeconfig(host)}")) or {}
    utilisateur = ((conf.get("users") or [{}])[0].get("user") or {})
    porte = base64.b64decode(utilisateur.get("client-certificate-data") or "")
    if not porte and utilisateur.get("client-certificate"):
        porte = host.check_output(f"sudo cat {utilisateur['client-certificate']}").encode()
    qui = _comme_camille(host, "auth whoami -o json")
    nom = (json.loads(qui.stdout).get("status") or {}).get("userInfo", {}).get("username") if qui.rc == 0 else None
    assert delivre and porte.strip() == delivre.strip() and nom == "camille", message(
        en=f"Camille's kubeconfig does not carry the certificate the API issued for her request, or the API does "
        f"not identify her (seen as {nom!r}). The certificate comes from the request, not from the CA key.",
        fr=f"Le kubeconfig de camille ne porte pas le certificat que l'API a délivré pour sa demande, ou l'API ne "
        f"l'identifie pas (vue comme {nom!r}). Le certificat vient de la demande, pas de la clé de la CA.",
    )


def test_camille_lit_les_pods_d_equipe_web(host):
    res = _comme_camille(host, f"-n {NS} get pods -o name")
    assert res.rc == 0 and "pod/vitrine" in res.stdout, message(
        en=f"With her kubeconfig, camille cannot list the Pods of {NS}: {res.stderr.strip()[:160]}",
        fr=f"Avec son kubeconfig, camille ne peut pas lister les Pods d'{NS} : {res.stderr.strip()[:160]}",
    )


def test_camille_ne_peut_rien_de_plus(host):
    _kubeconfig(host)
    essais = [("delete", "pods", NS), ("create", "deployments", NS), ("get", "secrets", NS),
              ("list", "pods", "default"), ("list", "pods", "kube-system"), ("list", "nodes", "")]
    accordes = []
    for verbe, ressource, ns in essais:
        option = f"-n {ns}" if ns else ""
        if _comme_camille(host, f"auth can-i {verbe} {ressource} {option}").stdout.strip() == "yes":
            accordes.append(f"{verbe} {ressource}" + (f" -n {ns}" if ns else ""))
    assert not accordes, message(
        en=f"camille can do more than read the Pods of {NS}: {accordes}.",
        fr=f"camille peut plus que lire les Pods d'{NS} : {accordes}.",
    )
