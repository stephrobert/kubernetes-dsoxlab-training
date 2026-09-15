"""test_functional.py : cka-troubleshoot-dns

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Le candidat
arrive au résultat par le chemin qu'il veut, et seul le résultat compte.

Trois affirmations. La première regarde le composant DNS ; les deux autres
regardent son EFFET depuis le Pod client, et ce sont elles qui prouvent
quelque chose : un CoreDNS « Running » qui ne répondrait pas ne passerait pas.
`nslookup` interroge le serveur DNS du cluster et ignore `/etc/hosts` : une
rustine dans le Pod client ne ferait passer aucun test.

Ce fichier interroge le cluster directement, avec `kubectl`. Il appelait
jusqu'ici la bibliothèque de checks héritée de K8sExamLab, déposée sous
`/opt/checks` par le setup : c'était le dernier lab du catalogue à en
dépendre. La règle est désormais sans exception : un lab fini ne dépend
d'aucun reste de l'ancêtre archivé, parce qu'une dépendance runtime déposée
par le setup est une pièce de plus à maintenir, invisible depuis le test et
introuvable pour qui le lit.
"""

from __future__ import annotations

import pytest

from conftest import lab_host, lab_target_host

KUBECTL = "sudo -E kubectl --kubeconfig /etc/kubernetes/admin.conf"
NAMESPACE = "app"
CLIENT = "client"
NOM = "web-svc.app.svc.cluster.local"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, commande: str):
    """Joue une commande kubectl sur le control plane.

    Rend (code, sortie standard, diagnostic). Les trois sont SÉPARÉS, et ce
    n'est pas un détail de style.

    La première version de ce fichier concaténait stdout et stderr, puis
    concluait « chaîne vide = aucun Pod ». Elle concluait donc toujours
    l'inverse : le client SSH écrit « Warning: Permanently added '10.10.50.11'
    (ED25519) to the list of known hosts. » sur stderr, et la chaîne n'était
    jamais vide. Le test passait AVANT le travail, sur un cluster où CoreDNS
    était à zéro replica, exactement ce que la règle des deux sens attrape.

    Un test qui mesure la présence de quelque chose lit la SORTIE STANDARD.
    stderr sert aux messages d'erreur, pas à décider.
    """
    res = host.run(f"{KUBECTL} {commande}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _dans_le_client(host, commande: str):
    """Exécute une commande DANS le Pod client.

    Le délai est borné : un Pod qui ne répond pas doit faire échouer le test,
    pas suspendre la campagne de validation.
    """
    return _kubectl(
        host,
        f"-n {NAMESPACE} exec {CLIENT} --request-timeout=30s -- {commande}",
    )


# ----------------------------------------------------------------------
# 1. Le composant DNS du cluster tourne.
# ----------------------------------------------------------------------
def test_coredns_tourne(host):
    """Sans Pod CoreDNS, le Service kube-dns n'a personne derrière lui."""
    rc, pods, diagnostic = _kubectl(
        host,
        "-n kube-system get pods -l k8s-app=kube-dns "
        "--field-selector=status.phase=Running "
        "-o jsonpath='{.items[*].metadata.name}'",
    )
    assert rc == 0, f"kubectl a échoué sur le control plane : {diagnostic}"
    assert pods, (
        "Aucun Pod CoreDNS ne tourne dans kube-system. Sans lui, aucun nom de "
        "service ne se résout dans le cluster. Regardez le Deployment coredns, "
        "son nombre de replicas souhaités et prêts, et les events du namespace."
    )


# ----------------------------------------------------------------------
# 2. La preuve qui compte : le client résout le nom.
# ----------------------------------------------------------------------
def test_le_client_resout_le_service(host):
    """Un CoreDNS présent mais muet ne passerait pas ce test.

    `nslookup` interroge le serveur déclaré dans le resolv.conf du Pod, donc
    le Service kube-dns. Il ne lit pas `/etc/hosts` : une entrée ajoutée à la
    main dans le Pod ne ferait pas passer ce test.
    """
    rc, _, diagnostic = _dans_le_client(host, f"nslookup {NOM}")
    assert rc == 0, (
        f"Le Pod {CLIENT} ne résout pas {NOM}. Le Service kube-dns existe "
        "toujours et son adresse est dans le resolv.conf du Pod, mais un "
        "Service sans endpoint ne répond à personne : vérifiez ce qui se tient "
        f"derrière lui, et attendez que ses Pods soient prêts. Sortie : {diagnostic}"
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
    rc, _, diagnostic = _dans_le_client(
        host, f"wget -q -O- --timeout=5 --tries=1 http://{NOM}"
    )
    if rc != 0:
        dns_rc, _, _ = _dans_le_client(host, f"nslookup {NOM}")
        assert dns_rc == 0, (
            f"La requête HTTP vers {NOM} échoue, et le nom ne se résout pas "
            "non plus : c'est le DNS du cluster qu'il faut réparer d'abord, "
            f"le test précédent dit où regarder. Sortie : {diagnostic}"
        )
    assert rc == 0, (
        f"Le nom {NOM} se résout, mais la requête HTTP échoue. Le DNS n'est "
        "donc plus en cause : regardez le Service web-svc, son selector, ses "
        f"endpoints, et l'état du Pod web. Sortie : {diagnostic}"
    )
