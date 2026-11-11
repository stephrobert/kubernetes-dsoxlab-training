"""test_functional.py : k8s-atteindre-une-application

Ces tests lisent le Service echo, ses EndpointSlices et le relevé
~/acces/releve.txt. Un test vérifie un seul état demandé par l'énoncé.

Le tunnel est un processus local, il ne laisse aucun objet dans le cluster :
c'est sa réponse qui est jugée. Sur /hostname, agnhost répond le nom de son
Pod ; la valeur consignée doit être le nom d'un Pod echo qui existe.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/boutique.kubeconfig"
NS = "acces"
RELEVE = f"~/{NS}/releve.txt"


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
# 3. La réponse lue à travers le tunnel.
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
    pods = _pods_echo(host)
    assert nom in pods, message(
        en=f"pod-du-tunnel is {valeur!r}, which is not an echo Pod {sorted(pods)}. Through a "
        "port-forward tunnel to the Service, ask http://localhost:<local port>/hostname: "
        "agnhost answers the name of the Pod the tunnel is attached to. Reread the section of "
        "the lesson on a tunnel to a Service.",
        fr=f"pod-du-tunnel vaut {valeur!r}, qui n'est pas un Pod echo {sorted(pods)}. À travers "
        "un tunnel port-forward vers le Service, demandez http://localhost:<port local>/hostname : "
        "agnhost répond le nom du Pod auquel le tunnel est attaché. Relisez la section de la "
        "leçon sur le tunnel vers un Service.",
    )
