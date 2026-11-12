"""test_functional.py : k8s-atteindre-une-application

Ces tests lisent le Service echo, ses EndpointSlices et le relevé
~/acces/releve.txt. Un test vérifie un seul état demandé par l'énoncé.

Le tunnel est un processus local, il ne laisse aucun objet dans le cluster.
Il doit donc rester OUVERT pendant la vérification, sur le port local 18080 :
le correcteur lit la liste des processus pour s'assurer qu'il vise le Service,
puis fait lui-même une requête par ce port. Sur /hostname, agnhost répond le nom
de son Pod, et le relevé doit nommer CE Pod-là : un nom recopié depuis
kubectl get pods, sans tunnel, ne passe pas.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "acces"
RELEVE = f"~/{NS}/releve.txt"
PORT_LOCAL = 18080


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} -n {NS} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _service(host) -> dict:
    svc = _json(host, "get service echo")
    assert svc is not None, message(
        en=f"No Service echo in {NS}: kubectl expose creates it from the Deployment.",
        fr=f"Aucun Service echo dans {NS} : kubectl expose le crée depuis le Deployment.",
    )
    return svc


def _pods_echo(host) -> set[str]:
    pods = (_json(host, "get pods -l app=echo") or {}).get("items") or []
    return {p["metadata"]["name"] for p in pods if not p["metadata"].get("deletionTimestamp")}


# ----------------------------------------------------------------------
# 1. Le Service sur les bons ports.
# ----------------------------------------------------------------------
def test_le_service_echo_expose_80_vers_8080(host):
    svc = _service(host)
    ports = [(p.get("port"), p.get("targetPort")) for p in svc["spec"].get("ports") or []]
    assert (80, 8080) in ports, message(
        en=f"The Service echo carries the ports {ports} (port, targetPort), expected 80 towards "
        "8080. Without --target-port, kubectl expose reuses --port: the Pods listen on 8080.",
        fr=f"Le Service echo porte les ports {ports} (port, targetPort), attendu 80 vers 8080. "
        "Sans --target-port, kubectl expose reprend --port : les Pods écoutent sur 8080.",
    )


# ----------------------------------------------------------------------
# 2. Les endpoints prêts.
# ----------------------------------------------------------------------
def test_le_service_echo_compte_deux_endpoints_prets(host):
    _service(host)
    tranches = (_json(host, "get endpointslice -l kubernetes.io/service-name=echo") or {}).get("items") or []
    prets = {
        adresse
        for tranche in tranches
        for point in tranche.get("endpoints") or []
        if (point.get("conditions") or {}).get("ready")
        for adresse in point.get("addresses") or []
    }
    assert len(prets) == 2, message(
        en=f"The Service echo counts {len(prets)} ready endpoint(s), expected 2, one per Pod. "
        "Its selector must match the labels of the echo Pods: kubectl expose copies it from "
        "the Deployment.",
        fr=f"Le Service echo compte {len(prets)} endpoint(s) prêt(s), attendu 2, un par Pod. Son "
        "sélecteur doit correspondre aux labels des Pods echo : kubectl expose le copie depuis "
        "le Deployment.",
    )


# ----------------------------------------------------------------------
# 3. Un tunnel vers le Service est ouvert sur le port local 18080.
# ----------------------------------------------------------------------
def _tunnels(host) -> list[str]:
    """Les lignes de commande des port-forward qui écoutent sur le port local."""
    res = host.run("ps -eo args")
    return [
        ligne for ligne in res.stdout.splitlines()
        if "port-forward" in ligne and f"{PORT_LOCAL}:" in ligne and "ps -eo" not in ligne
    ]


def _vise_le_service(ligne: str) -> bool:
    return any(f"{genre}/echo" in ligne.split() for genre in ("svc", "service", "services"))


def _reponse_du_tunnel(host) -> str:
    return host.run(f"curl -s --max-time 4 http://127.0.0.1:{PORT_LOCAL}/hostname").stdout.strip()


def test_un_tunnel_vers_le_service_repond_sur_18080(host):
    tunnels = _tunnels(host)
    reponse = _reponse_du_tunnel(host)
    vers_le_service = any(_vise_le_service(t) for t in tunnels)
    pods = _pods_echo(host)
    assert vers_le_service and reponse in pods, message(
        en=f"Tunnels open on local port {PORT_LOCAL}: {tunnels or 'none'}; a request through that port answers "
        f"{reponse or 'nothing'!r}. Expected a kubectl port-forward to the Service echo, still running during "
        f"the check, whose request answers the name of an echo Pod {sorted(pods)}.",
        fr=f"Tunnels ouverts sur le port local {PORT_LOCAL} : {tunnels or 'aucun'} ; une requête par ce port "
        f"répond {reponse or 'rien'!r}. Attendu un kubectl port-forward vers le Service echo, toujours ouvert "
        f"pendant la vérification, dont la requête répond le nom d'un Pod echo {sorted(pods)}.",
    )


# ----------------------------------------------------------------------
# 4. Le relevé nomme le Pod qui répond par ce tunnel.
# ----------------------------------------------------------------------
def test_le_pod_qui_repond_par_le_tunnel_est_consigne(host):
    fichier = host.file(f"{_maison(host)}/{NS}/releve.txt")
    valeur = ""
    if fichier.exists:
        for ligne in fichier.content_string.splitlines():
            if ligne.strip().lower().startswith("pod-du-tunnel:"):
                valeur = ligne.split(":", 1)[1].strip().strip("`'\"")
    assert valeur, message(
        en=f"The key 'pod-du-tunnel' of {RELEVE} has no value.",
        fr=f"La clé 'pod-du-tunnel' de {RELEVE} n'a pas de valeur.",
    )
    nom = valeur.split("/", 1)[1] if valeur.startswith("pod/") else valeur
    reponse = _reponse_du_tunnel(host)
    assert reponse and nom == reponse, message(
        en=f"pod-du-tunnel is {valeur!r}, and the tunnel on local port {PORT_LOCAL} answers "
        f"{reponse or 'nothing'!r}. Expected the name of the Pod answering through that tunnel: a "
        "tunnel to a Service attaches to a single Pod, chosen when it starts. Reread the section "
        "of the lesson on a tunnel to a Service.",
        fr=f"pod-du-tunnel vaut {valeur!r}, et le tunnel du port local {PORT_LOCAL} répond "
        f"{reponse or 'rien'!r}. Attendu le nom du Pod qui répond par ce tunnel : un tunnel vers un "
        "Service s'attache à un seul Pod, choisi à son lancement. Relisez la section de la leçon "
        "sur le tunnel vers un Service.",
    )
