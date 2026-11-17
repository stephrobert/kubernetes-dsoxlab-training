"""test_functional.py : cks-fermer-l-acces-reseau-au-noeud

Ces tests lisent l'état de k8s-w2.lab, jamais les commandes tapées : le jeu
de règles chargé (nft -j list ruleset), de VRAIES connexions neuves vers ses
ports depuis k8s-w1.lab (un nœud, pas un poste d'administration) et depuis le
control plane, le trafic des Pods à travers le nœud, et le service nftables
qui rechargera les règles au démarrage.

Les connexions sont toujours NEUVES : une règle `ct state established` laisse
passer une connexion déjà ouverte, et un test qui réutiliserait une connexion
vivante verrait un faux vert (mesuré le 2026-11-16, série 2 CKS-A, M4).

Aucun test n'est vrai avant le travail : le setup ne pose aucun pare-feu. Les
tests « les flux du cluster passent » et « les règles survivent au
redémarrage » exigent donc aussi qu'une chaîne d'entrée en `drop` soit
chargée.

Deux triches sont refusées par construction : tout fermer (le kubelet, SSH
depuis le control plane et le trafic des Pods doivent passer), et un pare-feu
chargé à la main sans persistance (le service nftables doit le recharger).
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_host_ip, message

NOEUD = "k8s-w2.lab"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS = "sonde-pare-feu"
BUSYBOX = "busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
NGINX = "nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d"


@pytest.fixture(scope="module")
def host():
    return lab_host(NOEUD)


@pytest.fixture(scope="module")
def w1():
    return lab_host("k8s-w1.lab")


@pytest.fixture(scope="module")
def cp():
    return lab_host("k8s-cp.lab")


@pytest.fixture(scope="module")
def ip_noeud():
    return lab_host_ip(NOEUD)


def _chaines_d_entree_en_drop(host) -> list[str]:
    res = host.run("sudo nft -j list ruleset")
    if res.rc != 0 or not res.stdout.strip():
        return []
    chaines = []
    for objet in json.loads(res.stdout).get("nftables", []):
        chaine = objet.get("chain")
        if chaine and chaine.get("hook") == "input" and chaine.get("policy") == "drop":
            chaines.append(f"{chaine.get('family')} {chaine.get('table')} {chaine.get('name')}")
    return chaines


def _exiger_le_pare_feu(host) -> None:
    assert _chaines_d_entree_en_drop(host), message(
        en=f"No input chain with policy drop is loaded on {NOEUD}: sudo nft list ruleset shows the rules "
        "actually loaded.",
        fr=f"Aucune chaîne d'entrée en policy drop n'est chargée sur {NOEUD} : sudo nft list ruleset montre "
        "les règles réellement chargées.",
    )


def _joint(source, ip: str, port: int) -> bool:
    return source.run(f"nc -z -w 3 {ip} {port}").rc == 0


def test_le_pare_feu_ferme_le_reste(host, w1, ip_noeud):
    _exiger_le_pare_feu(host)
    assert not _joint(w1, ip_noeud, 10256), message(
        en=f"Port 10256 (kube-proxy health) of {NOEUD} still answers k8s-w1: the rest is not closed.",
        fr=f"Le port 10256 (santé de kube-proxy) de {NOEUD} répond encore à k8s-w1 : le reste n'est pas fermé.",
    )
    assert not _joint(w1, ip_noeud, 22), message(
        en=f"SSH on {NOEUD} still answers k8s-w1, which is neither the administration workstation nor the "
        "control plane.",
        fr=f"SSH sur {NOEUD} répond encore à k8s-w1, qui n'est ni le poste d'administration ni le control "
        "plane.",
    )


def test_les_flux_du_cluster_passent(host, w1, cp, ip_noeud):
    _exiger_le_pare_feu(host)
    assert _joint(w1, ip_noeud, 10250), message(
        en=f"Port 10250 (kubelet) of {NOEUD} refuses k8s-w1: the nodes must reach it.",
        fr=f"Le port 10250 (kubelet) de {NOEUD} refuse k8s-w1 : les nœuds doivent l'atteindre.",
    )
    assert _joint(cp, ip_noeud, 22), message(
        en=f"SSH on {NOEUD} refuses the control plane: administration goes through it.",
        fr=f"SSH sur {NOEUD} refuse le control plane : l'administration passe par lui.",
    )
    cp.run(f"{KUBECTL} delete namespace {NS} --ignore-not-found --wait=true --timeout=90s")
    cp.run(f"{KUBECTL} create namespace {NS}")
    manifeste = {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {"apiVersion": "v1", "kind": "Pod",
             "metadata": {"name": "web", "namespace": NS, "labels": {"app": "web"}},
             "spec": {"nodeName": NOEUD, "containers": [{"name": "nginx", "image": NGINX}]}},
            {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "web", "namespace": NS},
             "spec": {"selector": {"app": "web"}, "ports": [{"port": 80, "targetPort": 80}]}},
            {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "client", "namespace": NS},
             "spec": {"nodeName": "k8s-w1.lab",
                      "containers": [{"name": "c", "image": BUSYBOX, "command": ["sleep", "600"]}]}},
        ],
    }
    cp.run(f"echo '{json.dumps(manifeste)}' | {KUBECTL} apply -f -")
    try:
        pret = cp.run(f"{KUBECTL} -n {NS} wait --for=condition=Ready pod/web pod/client --timeout=120s")
        assert pret.rc == 0, message(
            en=f"The probe Pods do not start: {pret.stderr.strip()}",
            fr=f"Les Pods de sonde ne démarrent pas : {pret.stderr.strip()}",
        )
        res = cp.run(f"{KUBECTL} -n {NS} exec client -- wget -qO- -T 5 http://web.{NS}/")
        assert "Welcome to nginx" in res.stdout, message(
            en=f"A Pod of k8s-w1 no longer reaches, through a Service, a Pod of {NOEUD}: the network plugin "
            "ports (Calico: TCP 179, UDP 4789) must stay open to the nodes.",
            fr=f"Un Pod de k8s-w1 n'atteint plus, par un Service, un Pod de {NOEUD} : les ports du plugin "
            "réseau (Calico : TCP 179, UDP 4789) doivent rester ouverts aux nœuds.",
        )
        res = cp.run(f"{KUBECTL} -n {NS} logs web --request-timeout=15s")
        assert res.rc == 0, message(
            en=f"kubectl logs on a Pod of {NOEUD} fails ({res.stderr.strip()}): the API server reaches the "
            "kubelet on port 10250.",
            fr=f"kubectl logs sur un Pod de {NOEUD} échoue ({res.stderr.strip()}) : l'API server joint le "
            "kubelet sur le port 10250.",
        )
    finally:
        cp.run(f"{KUBECTL} delete namespace {NS} --ignore-not-found --wait=true --timeout=120s")


def test_les_regles_survivent_au_redemarrage(host, cp):
    _exiger_le_pare_feu(host)
    assert host.service("nftables").is_enabled, message(
        en="nftables.service is not enabled: the rules would be gone after a reboot.",
        fr="nftables.service n'est pas activé : les règles disparaîtraient au redémarrage.",
    )
    conf = host.run("sudo cat /etc/nftables.conf").stdout
    lignes = [ligne.strip() for ligne in conf.splitlines() if not ligne.strip().startswith("#")]
    assert "flush ruleset" not in lignes, message(
        en="/etc/nftables.conf still starts with flush ruleset: at boot it would erase the rules of "
        "kube-proxy and of the network plugin.",
        fr="/etc/nftables.conf contient encore flush ruleset : au démarrage, il effacerait les règles de "
        "kube-proxy et du plugin réseau.",
    )
    res = host.run("sudo nft -c -f /etc/nftables.conf")
    assert res.rc == 0, message(
        en=f"sudo nft -c -f /etc/nftables.conf fails: {res.stderr.strip()}",
        fr=f"sudo nft -c -f /etc/nftables.conf échoue : {res.stderr.strip()}",
    )
    texte = conf
    for inclus in re.findall(r'^\s*include\s+"([^"]+)"', conf, flags=re.M):
        texte += host.run(f"sudo cat {inclus}").stdout
    assert "hook input" in texte and "policy drop" in texte, message(
        en="The file loaded at boot (/etc/nftables.conf and its includes) holds no input chain with "
        "policy drop.",
        fr="Le fichier chargé au démarrage (/etc/nftables.conf et ses include) ne contient aucune chaîne "
        "d'entrée en policy drop.",
    )

    # La preuve : un VRAI redémarrage. Le jeu de règles doit revenir, et le
    # nœud doit repasser Ready (kube-proxy et Calico intacts).
    host.run("sudo systemd-run --on-active=2 systemctl reboot")
    time.sleep(20)
    for _ in range(36):
        if host.run("systemctl is-active kubelet").stdout.strip() == "active":
            break
        time.sleep(5)
    time.sleep(15)
    for _ in range(36):
        etat = cp.run(
            f"{KUBECTL} get node {NOEUD} -o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'"
        ).stdout.strip()
        if etat == "True":
            break
        time.sleep(5)
    assert etat == "True", message(
        en=f"{NOEUD} does not come back Ready after a reboot ({etat}).",
        fr=f"{NOEUD} ne revient pas Ready après un redémarrage ({etat}).",
    )
    assert _chaines_d_entree_en_drop(host), message(
        en=f"After a reboot of {NOEUD}, no input chain with policy drop is loaded: the rules did not persist.",
        fr=f"Après un redémarrage de {NOEUD}, aucune chaîne d'entrée en policy drop n'est chargée : les "
        "règles n'ont pas persisté.",
    )
