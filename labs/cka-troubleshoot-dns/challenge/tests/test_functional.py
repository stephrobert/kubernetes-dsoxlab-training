"""test_functional.py : cka-troubleshoot-dns

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Le candidat
arrive au résultat par le chemin qu'il veut, et seul le résultat compte.

Quatre affirmations. Les deux premières regardent le composant DNS : ses
réplicas, puis la zone que sa configuration sert. Les deux autres regardent son
EFFET depuis le Pod client, et ce sont elles qui prouvent quelque chose : un
CoreDNS « Running » qui ne répondrait pas ne passerait pas.

La préparation pose DEUX pannes. CoreDNS est à zéro réplica, et son Corefile
déclare la zone cluster.locale au lieu de cluster.local. La seconde ne se voit
qu'une fois la première réparée : CoreDNS revient Running et Ready, charge une
configuration valide, et la résolution échoue quand même.
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

import time

import pytest

from conftest import lab_host, lab_target_host, message

KUBECTL = "sudo -E kubectl --kubeconfig /etc/kubernetes/admin.conf"
NAMESPACE = "app"
CLIENT = "client"
NOM = "web-svc.app.svc.cluster.local"
ATTENTE = 120
# La relecture du Corefile a son propre budget : les deux attentes tiennent
# ensemble sous les 300 s que dsoxlab accorde à la suite.
ATTENTE_RELECTURE = 90
PAS = 5


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
def test_coredns_tourne_comme_kubeadm_le_pose(host):
    """Sans Pod CoreDNS, le Service kube-dns n'a personne derrière lui.

    kubeadm pose CoreDNS à deux réplicas : un seul réplica résout aussi, mais ce
    n'est pas le cluster rendu dans son état d'origine. L'attente ne s'ouvre
    que si des réplicas sont demandés, donc jamais sur l'état de départ.
    """
    def lire() -> tuple[int, int]:
        rc, sortie, _ = _kubectl(
            host, "-n kube-system get deployment coredns -o jsonpath='{.spec.replicas} {.status.readyReplicas}'")
        valeurs = [*sortie.split(), "0", "0"][:2] if rc == 0 else ["0", "0"]
        return int(valeurs[0] or 0), int(valeurs[1] or 0)

    voulus, prets = lire()
    fin = time.monotonic() + (ATTENTE if voulus else 0)
    while prets != voulus and time.monotonic() < fin:
        time.sleep(PAS)
        voulus, prets = lire()
    assert voulus == 2 and prets == 2, message(
        en=f"The coredns Deployment asks for {voulus} replica(s), {prets} ready. Expected 2 and 2, as kubeadm sets "
        "it up: without a CoreDNS Pod, no service name resolves in the cluster.",
        fr=f"Le Deployment coredns demande {voulus} réplica(s), {prets} prêt(s). Attendu 2 et 2, comme kubeadm le "
        "pose : sans Pod CoreDNS, aucun nom de service ne se résout dans le cluster.",
    )


# ----------------------------------------------------------------------
# 2. La configuration de CoreDNS sert la zone du cluster.
# ----------------------------------------------------------------------
def _zones_du_plugin_kubernetes(host) -> list[str]:
    rc, corefile, _ = _kubectl(host, "-n kube-system get configmap coredns -o jsonpath='{.data.Corefile}'")
    for ligne in corefile.splitlines() if rc == 0 else []:
        mots = ligne.split()
        if mots and mots[0] == "kubernetes":
            return [m for m in mots[1:] if m != "{"]
    return []


def test_le_corefile_sert_la_zone_du_cluster(host):
    zones = _zones_du_plugin_kubernetes(host)
    assert "cluster.local" in zones, message(
        en=f"In the coredns ConfigMap, the kubernetes plugin serves the zones {zones or 'none'}. Expected "
        "cluster.local, the cluster's domain: names outside the zones it serves go to the upstream DNS, which "
        "does not know them.",
        fr=f"Dans la ConfigMap coredns, le plugin kubernetes sert les zones {zones or 'aucune'}. Attendu "
        "cluster.local, le domaine du cluster : les noms hors des zones qu'il sert partent vers le DNS amont, qui "
        "ne les connaît pas.",
    )


# ----------------------------------------------------------------------
# 3. La preuve qui compte : le client résout le nom.
# ----------------------------------------------------------------------
def test_le_client_resout_le_service(host):
    """Un CoreDNS présent mais muet ne passerait pas ce test.

    `nslookup` interroge le serveur déclaré dans le resolv.conf du Pod, donc
    le Service kube-dns. Il ne lit pas `/etc/hosts` : une entrée ajoutée à la
    main dans le Pod ne ferait pas passer ce test.
    """
    rc, _, diagnostic = _dans_le_client(host, f"nslookup {NOM}")
    # CoreDNS relit sa ConfigMap de lui-même, mais pas tout de suite : le temps
    # que le kubelet la propage, puis que le plugin reload la recharge. On
    # n'attend que si la configuration est déjà juste.
    if rc != 0 and "cluster.local" in _zones_du_plugin_kubernetes(host):
        fin = time.monotonic() + ATTENTE_RELECTURE
        while rc != 0 and time.monotonic() < fin:
            time.sleep(PAS)
            rc, _, diagnostic = _dans_le_client(host, f"nslookup {NOM}")
    assert rc == 0, message(
        en=f"Pod {CLIENT} does not resolve {NOM}. The kube-dns Service's address is in the Pod's resolv.conf: "
        "either nothing answers behind it, or what answers does not serve the cluster's zone. A CoreDNS that is "
        f"Running and Ready can still answer NXDOMAIN. Output: {diagnostic}",
        fr=f"Le Pod {CLIENT} ne résout pas {NOM}. L'adresse du Service kube-dns est dans le resolv.conf du Pod : "
        "soit rien ne répond derrière lui, soit ce qui répond ne sert pas la zone du cluster. Un CoreDNS Running "
        f"et Ready peut répondre NXDOMAIN quand même. Sortie : {diagnostic}",
    )


# ----------------------------------------------------------------------
# 4. Et il joint réellement le Service par ce nom.
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
        assert dns_rc == 0, message(
            en=f"The HTTP request to {NOM} fails, and the name does not resolve "
            "either: it is the cluster's DNS that must be fixed first, "
            f"and the previous test says where to look. Output: {diagnostic}",
            fr=f"La requête HTTP vers {NOM} échoue, et le nom ne se résout pas "
            "non plus : c'est le DNS du cluster qu'il faut réparer d'abord, "
            f"le test précédent dit où regarder. Sortie : {diagnostic}",
        )
    assert rc == 0, message(
        en=f"Name {NOM} resolves, but the HTTP request fails. DNS is therefore "
        "no longer at fault: look at the web-svc Service, its selector, its "
        f"endpoints, and the state of the web Pod. Output: {diagnostic}",
        fr=f"Le nom {NOM} se résout, mais la requête HTTP échoue. Le DNS n'est "
        "donc plus en cause : regardez le Service web-svc, son selector, ses "
        f"endpoints, et l'état du Pod web. Sortie : {diagnostic}",
    )
