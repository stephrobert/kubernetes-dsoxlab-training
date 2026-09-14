"""test_functional.py : cka-troubleshoot-dns

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Le candidat
arrive au résultat par le chemin qu'il veut, et seul le résultat compte.

Trois affirmations. La première regarde le composant DNS ; les deux autres
regardent son EFFET depuis le Pod client, et ce sont elles qui prouvent
quelque chose : un CoreDNS « Running » qui ne répondrait pas ne passerait pas.
`nslookup` interroge le serveur DNS du cluster et ignore `/etc/hosts` : une
rustine dans le Pod client ne ferait passer aucun test.

Chaque test appelle la bibliothèque de checks héritée de K8sExamLab, déposée
sous /opt/checks par le setup. Elle interroge le cluster avec kubectl.
"""

from __future__ import annotations

import pytest

from conftest import lab_host, lab_target_host

DISPATCH = "/opt/checks/dispatch.sh"
NAMESPACE = "app"
CLIENT = "client"
NOM = "web-svc.app.svc.cluster.local"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _check(host, *args: str):
    """Joue un check hérité et rend (code de retour, sortie)."""
    cmd = " ".join(str(a) for a in args)
    res = host.run(f"sudo -E bash {DISPATCH} {cmd}")
    return res.rc, (res.stdout + res.stderr).strip()


# ----------------------------------------------------------------------
# 1. Le composant DNS du cluster tourne.
# ----------------------------------------------------------------------
def test_coredns_tourne(host):
    """Sans Pod CoreDNS, le Service kube-dns n'a personne derrière lui."""
    rc, sortie = _check(host, "coredns-running")
    assert rc == 0, (
        "Aucun Pod CoreDNS ne tourne dans kube-system. Sans lui, aucun nom de "
        "service ne se résout dans le cluster. Regardez le Deployment coredns, "
        "son nombre de replicas souhaités et prêts, et les events du namespace. "
        f"Sortie : {sortie}"
    )


# ----------------------------------------------------------------------
# 2. La preuve qui compte : le client résout le nom.
# ----------------------------------------------------------------------
def test_le_client_resout_le_service(host):
    """Un CoreDNS présent mais muet ne passerait pas ce test."""
    rc, sortie = _check(host, "dns-resolves", NAMESPACE, CLIENT, NOM)
    assert rc == 0, (
        f"Le Pod {CLIENT} ne résout pas {NOM}. Le Service kube-dns existe "
        "toujours et son adresse est dans le resolv.conf du Pod, mais un "
        "Service sans endpoint ne répond à personne : vérifiez ce qui se tient "
        f"derrière lui, et attendez que ses Pods soient prêts. Sortie : {sortie}"
    )


# ----------------------------------------------------------------------
# 3. Et il joint réellement le Service par ce nom.
# ----------------------------------------------------------------------
def test_le_client_joint_le_service_en_http(host):
    """Résoudre un nom ne suffit pas : la requête doit aboutir.

    Le message distingue deux pannes : tant que le nom ne se résout pas, c'est
    encore le DNS ; s'il se résout et que HTTP échoue, c'est le Service ou le
    Pod. Un message qui accuserait le Service pendant que le DNS est en panne
    enverrait l'apprenant au mauvais endroit.
    """
    rc, sortie = _check(host, "http-reachable", NAMESPACE, CLIENT, NOM)
    if rc != 0:
        dns_rc, _ = _check(host, "dns-resolves", NAMESPACE, CLIENT, NOM)
        assert dns_rc == 0, (
            f"La requête HTTP vers {NOM} échoue, et le nom ne se résout pas "
            "non plus : c'est le DNS du cluster qu'il faut réparer d'abord, "
            f"le test précédent dit où regarder. Sortie : {sortie}"
        )
    assert rc == 0, (
        f"Le nom {NOM} se résout, mais la requête HTTP échoue. Le DNS n'est "
        "donc plus en cause : regardez le Service web-svc, son selector, ses "
        f"endpoints, et l'état du Pod web. Sortie : {sortie}"
    )
