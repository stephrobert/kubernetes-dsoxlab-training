"""test_functional.py : k8s-relier-deux-clusters

Trois tests, un par état demandé. Ils lisent les deux clusters depuis
ha-cp1.lab (kubeconfig d'administration de cluster-1, et celui de cluster-2
posé par le setup), et font passer de vraies requêtes depuis un Pod de
cluster-1. Jamais un fichier de l'apprenant.

Pourquoi lire la liste des nœuds de l'agent Cilium : c'est ce que le maillage
a réellement appris. Un ClusterMesh « connecté » dans la configuration Helm
mais dont l'agent ne voit pas le nœud distant ne fait passer aucun paquet.

Pourquoi douze requêtes au test 3 : un Service global répartit entre les
backends des deux clusters. Douze tirages rendent la probabilité de ne voir
qu'un cluster (2 x 0,5^12, moins de 0,05 %) négligeable.
"""

from __future__ import annotations

import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "mesh-demo"
KUBECONFIGS = {1: "/etc/kubernetes/admin.conf", 2: "/etc/kubernetes/cluster-2.conf"}
NOEUDS = {1: "ha-cp1.lab", 2: "ha-cp2.lab"}
REQUETES = 12
BUDGET_S = 120
PAS_S = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("ha-cp1.lab"))


def _kubectl(host, cluster: int, args: str):
    res = host.run(f"sudo kubectl --kubeconfig {KUBECONFIGS[cluster]} {args}")
    return res.rc, res.stdout.strip(), res.stderr.strip()


def _attendre(lire, pret, budget: float = BUDGET_S):
    valeur = lire()
    fin = time.monotonic() + budget
    while not pret(valeur) and time.monotonic() < fin:
        time.sleep(PAS_S)
        valeur = lire()
    return valeur


def _noeuds_vus(host, cluster: int) -> str:
    _, sortie, diag = _kubectl(host, cluster, "-n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg node list")
    return sortie or diag


def _annotation(host, cluster: int) -> str:
    _, valeur, _ = _kubectl(
        host, cluster,
        f"-n {NAMESPACE} get service echo -o jsonpath='{{.metadata.annotations.service\\.cilium\\.io/global}}'",
    )
    return valeur


# ----------------------------------------------------------------------
# 1. Chaque cluster voit le nœud de l'autre.
# ----------------------------------------------------------------------
def test_les_deux_clusters_se_voient(host):
    for local, distant in ((1, 2), (2, 1)):
        attendu = f"cluster-{distant}/{NOEUDS[distant]}"
        vus = _attendre(lambda local=local: _noeuds_vus(host, local), lambda s, a=attendu: a in s)
        assert attendu in vus, message(
            en=f"The Cilium agent of cluster-{local} does not see the node {attendu}: the two clusters are not "
            "connected. cilium clustermesh connect, run with both contexts, connects them both ways; cilium "
            "clustermesh status --wait tells when it is done. Its node list:\n" + vus,
            fr=f"L'agent Cilium de cluster-{local} ne voit pas le nœud {attendu} : les deux clusters ne sont pas "
            "reliés. cilium clustermesh connect, lancé avec les deux contextes, les relie dans les deux sens ; "
            "cilium clustermesh status --wait dit quand c'est fait. Sa liste de nœuds :\n" + vus,
        )


# ----------------------------------------------------------------------
# 2. Le Service echo est global dans les deux clusters.
# ----------------------------------------------------------------------
def test_le_service_echo_est_global_des_deux_cotes(host):
    lus = {c: _annotation(host, c) for c in (1, 2)}
    assert all(v == "true" for v in lus.values()), message(
        en=f"The annotation service.cilium.io/global of the Service echo is {lus}: it must be \"true\" in BOTH "
        "clusters. On one side only, the Service of the other side does not share its backends.",
        fr=f"L'annotation service.cilium.io/global du Service echo vaut {lus} : elle doit valoir \"true\" dans "
        "les DEUX clusters. D'un seul côté, le Service de l'autre ne partage pas ses backends.",
    )


# ----------------------------------------------------------------------
# 3. Depuis cluster-1, les deux clusters répondent.
# ----------------------------------------------------------------------
def test_le_client_recoit_des_reponses_des_deux_clusters(host):
    def tirer() -> set:
        vues = set()
        for _ in range(REQUETES):
            rc, sortie, _ = _kubectl(
                host, 1, f"-n {NAMESPACE} exec client -- wget -qO- -T 3 http://echo.{NAMESPACE}/"
            )
            vues.add(sortie if rc == 0 else "échec")
        return vues

    vues = _attendre(tirer, lambda v: {"reponse-de-cluster-1", "reponse-de-cluster-2"} <= v, budget=90)
    assert {"reponse-de-cluster-1", "reponse-de-cluster-2"} <= vues, message(
        en=f"From the Pod client of cluster-1, {REQUETES} requests to echo.{NAMESPACE} returned {sorted(vues)}: "
        "both clusters must answer. In an agent of cluster-1, cilium-dbg service list shows the backends of the "
        "Service, the remote ones included once the Service is global.",
        fr=f"Depuis le Pod client de cluster-1, {REQUETES} requêtes vers echo.{NAMESPACE} ont rendu {sorted(vues)} : "
        "les deux clusters doivent répondre. Dans un agent de cluster-1, cilium-dbg service list montre les "
        "backends du Service, ceux de l'autre cluster compris une fois le Service global.",
    )
