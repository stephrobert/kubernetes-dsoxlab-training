"""test_functional.py : cks-reduire-la-surface-du-noeud

Ces tests lisent l'état de k8s-w2.lab, jamais les commandes tapées : sockets
en écoute (ss), paquets installés (dpkg-query), unités systemd, et une vraie
connexion sur chaque port retiré.

Aucun test n'est vrai avant le travail : le setup laisse rpcbind (111),
vsftpd (21) et outil-debug.service (8000) en écoute sur toutes les
interfaces. Le test « le nœud sert encore Kubernetes » serait vrai au départ :
il exige donc aussi que la surface soit réduite.

Deux triches sont refusées par construction : arrêter rpcbind.service sans
traiter rpcbind.socket (la socket écoute encore sur 111), et retirer tout ce
qui écoute, kubelet compris (le nœud doit rester Ready et accueillir un Pod).
"""

from __future__ import annotations

import pytest

from conftest import lab_host, message

NOEUD = "k8s-w2.lab"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
# Ce qui écoute sur toutes les interfaces d'un worker du catalogue, relevé le
# 2026-11-17 sur k8s-w1.lab : sshd, bird (BGP de Calico), kubelet, kube-proxy,
# VXLAN de Calico, et le client DHCP lié à l'adresse du nœud. Plus calico-typha
# (5473) : l'opérateur Tigera en place selon le nombre de nœuds, et le
# 2026-11-17 l'un d'eux a atterri sur k8s-w2 entre deux passages du lab.
PORTS_ATTENDUS = {
    ("tcp", 22), ("tcp", 179), ("tcp", 5473), ("tcp", 10250), ("tcp", 10256), ("udp", 4789), ("udp", 68),
}
PORTS_RETIRES = (111, 21, 8000)
PAQUETS_RETIRES = ("rpcbind", "vsftpd")


@pytest.fixture(scope="module")
def host():
    return lab_host(NOEUD)


@pytest.fixture(scope="module")
def cp():
    return lab_host("k8s-cp.lab")


def _ecoute(host) -> set[tuple[str, int]]:
    """Sockets en écoute hors boucle locale : {(protocole, port)}."""
    res = host.run("sudo ss -Htuln")
    vus = set()
    for ligne in res.stdout.splitlines():
        champs = ligne.split()
        if len(champs) < 5:
            continue
        proto, locale = champs[0], champs[4]
        adresse, _, port = locale.rpartition(":")
        if adresse.startswith(("127.", "[::1]")) or "%lo" in adresse:
            continue
        if port.isdigit():
            vus.add((proto, int(port)))
    return vus


def _surface_reduite(host) -> None:
    en_trop = sorted(_ecoute(host) - PORTS_ATTENDUS)
    assert not en_trop, message(
        en=f"Still listening on every interface of {NOEUD}: {en_trop}. sudo ss -tulpn names the process.",
        fr=f"Écoute encore sur toutes les interfaces de {NOEUD} : {en_trop}. sudo ss -tulpn nomme le processus.",
    )


def test_aucun_port_superflu_n_ecoute(host, cp):
    _surface_reduite(host)
    ip = host.run("hostname -I").stdout.split()[0]
    for port in PORTS_RETIRES:
        res = cp.run(f"nc -z -w 3 {ip} {port}")
        assert res.rc != 0, message(
            en=f"Port {port} of {NOEUD} still accepts a connection from the control plane.",
            fr=f"Le port {port} de {NOEUD} accepte encore une connexion depuis le control plane.",
        )


def test_les_paquets_superflus_sont_purges(host):
    for paquet in PAQUETS_RETIRES:
        res = host.run(f"dpkg-query -W -f='${{Status}}' {paquet}")
        assert res.rc != 0 or "not-installed" in res.stdout or "config-files" in res.stdout, message(
            en=f"The package {paquet} is still installed on {NOEUD}: stopping a service is not removing it, "
            "the next upgrade or reboot brings it back.",
            fr=f"Le paquet {paquet} est encore installé sur {NOEUD} : arrêter un service ne le retire pas, "
            "la prochaine mise à jour ou le prochain redémarrage le relance.",
        )


def test_l_outil_de_debogage_ne_redemarre_plus(host):
    # `systemctl` est lu directement : host.service() de testinfra lève une
    # exception sur le code 4 (« not-found »), qui est justement l'état d'une
    # unité retirée (mesuré le 2026-11-17).
    actif = host.run("systemctl is-active outil-debug.service").stdout.strip()
    assert actif != "active", message(
        en="outil-debug.service is still running: it serves /etc over HTTP on port 8000.",
        fr="outil-debug.service tourne encore : il sert /etc en HTTP sur le port 8000.",
    )
    active_au_demarrage = host.run("systemctl is-enabled outil-debug.service").stdout.strip()
    assert active_au_demarrage in ("disabled", "masked", "not-found", ""), message(
        en=f"outil-debug.service is still {active_au_demarrage}: it would come back at the next boot. "
        "No package ships it, apt will not remove it.",
        fr=f"outil-debug.service est encore {active_au_demarrage} : il reviendrait au prochain démarrage. "
        "Aucun paquet ne le fournit, apt ne le retirera pas.",
    )


def test_le_noeud_sert_encore_kubernetes(host, cp):
    _surface_reduite(host)
    for service in ("kubelet", "containerd", "ssh"):
        assert host.service(service).is_running, message(
            en=f"{service} no longer runs on {NOEUD}: the node needs it. Restore it.",
            fr=f"{service} ne tourne plus sur {NOEUD} : le nœud en a besoin. Rétablissez-le.",
        )
    etat = cp.run(
        f"{KUBECTL} get node {NOEUD} -o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'"
    ).stdout.strip()
    assert etat == "True", message(
        en=f"{NOEUD} is not Ready ({etat}).",
        fr=f"{NOEUD} n'est pas Ready ({etat}).",
    )
    cp.run(f"{KUBECTL} -n default delete pod sonde-surface --ignore-not-found --wait=true")
    cp.run(
        f"{KUBECTL} -n default run sonde-surface --restart=Never "
        "--image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e "
        f"--overrides='{{\"spec\":{{\"nodeName\":\"{NOEUD}\"}}}}' -- sh -c 'echo pret; sleep 30'"
    )
    pret = cp.run(f"{KUBECTL} -n default wait --for=condition=Ready pod/sonde-surface --timeout=90s")
    cp.run(f"{KUBECTL} -n default delete pod sonde-surface --ignore-not-found --wait=true")
    assert pret.rc == 0, message(
        en=f"A Pod placed on {NOEUD} does not start: {pret.stderr.strip()}",
        fr=f"Un Pod placé sur {NOEUD} ne démarre pas : {pret.stderr.strip()}",
    )
