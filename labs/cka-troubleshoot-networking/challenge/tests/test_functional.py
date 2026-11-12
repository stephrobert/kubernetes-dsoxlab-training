"""test_functional.py : cka-troubleshoot-networking

Six tests, un par état demandé, sur les gestes de la leçon « Pod Networking ».
Ils lisent le cluster et font de vraies requêtes, jamais les commandes tapées.

Deux pièges sont fermés :
- avec Calico, le podCIDR d'un nœud ne dit pas où sont ses Pods : leurs
  adresses sortent de blocs /26 du pool du cluster. La plage attendue est celle
  du cluster, lue dans sa configuration ;
- le verdict « refus » ou « délai » ne se devine pas : le setup tire au sort
  lequel des deux Services refuse, et le mémorise.

Un Pod déplacé sur le control plane contournerait la panne sans la réparer :
cible doit tourner sur le worker, et sonde le joindre depuis l'autre nœud.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "reseau"
WORKER = "k8s-w1.lab"
PLAN = "k8s-cp.lab"
MEMOIRE = "/var/lib/dsoxlab/troubleshoot-networking.json"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Après la réparation, le nœud revient en quelques secondes et cible démarre.
# On n'attend que si le nœud est déjà revenu : l'état de départ se note vite.
BUDGET_S = 60
PAS_S = 3


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host(PLAN))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _objet(host, args: str) -> dict | None:
    res = _kubectl(host, f"{args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _maison(host) -> str:
    """Le répertoire de l'utilisateur du lab : testinfra agit en root par sudo."""
    return host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _fichier(host, nom: str) -> dict[str, str]:
    """Lit ~/reseau/<nom> de l'apprenant en paires « clé: valeur »."""
    res = host.run(f"cat {_maison(host)}/reseau/{nom}")
    paires = {}
    for ligne in res.stdout.splitlines() if res.rc == 0 else []:
        cle, sep, valeur = ligne.partition(":")
        if sep:
            paires[cle.strip().lower()] = valeur.strip()
    return paires


def _plages_du_cluster(host) -> dict[str, str]:
    brut = _kubectl(host, "-n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}'").stdout
    plages = {}
    for ligne in brut.splitlines():
        cle, _, valeur = ligne.strip().partition(":")
        if cle in ("podSubnet", "serviceSubnet"):
            plages[cle] = valeur.strip()
    return plages


def _ready(host, noeud: str) -> bool:
    n = _objet(host, f"get node {noeud}") or {}
    return any(c.get("type") == "Ready" and c.get("status") == "True" for c in (n.get("status") or {}).get("conditions") or [])


def _cible(host) -> dict | None:
    pod = _objet(host, f"-n {NAMESPACE} get pod cible")
    if pod is not None and (pod.get("status") or {}).get("phase") != "Running" and _ready(host, WORKER):
        fin = time.monotonic() + BUDGET_S
        while pod is not None and pod["status"].get("phase") != "Running" and time.monotonic() < fin:
            time.sleep(PAS_S)
            pod = _objet(host, f"-n {NAMESPACE} get pod cible") or pod
    return pod


# ----------------------------------------------------------------------
# 1. Les plages du cluster sont consignées.
# ----------------------------------------------------------------------
def test_les_plages_du_cluster_sont_consignees(host):
    vrai = _plages_du_cluster(host)
    ecrit = _fichier(host, "plages.txt")
    vu = (ecrit.get("pods"), ecrit.get("services"))
    attendu = (vrai.get("podSubnet"), vrai.get("serviceSubnet"))
    assert vu == attendu, message(
        en=f"~/reseau/plages.txt gives pods={vu[0]} and services={vu[1]}. Expected the ranges of the whole cluster, "
        "read in its configuration. With Calico, a node's podCIDR does not tell where its Pods' addresses come from.",
        fr=f"~/reseau/plages.txt donne pods={vu[0]} et services={vu[1]}. Attendu les plages du cluster entier, lues "
        "dans sa configuration. Avec Calico, le podCIDR d'un nœud ne dit pas d'où viennent les adresses de ses Pods.",
    )


# ----------------------------------------------------------------------
# 2. L'adresse de cible est consignée.
# ----------------------------------------------------------------------
def test_l_adresse_de_cible_est_consignee(host):
    pod = _cible(host)
    ip = ((pod or {}).get("status") or {}).get("podIP")
    ecrit = _fichier(host, "plages.txt").get("cible")
    assert ip and ecrit == ip, message(
        en=f"~/reseau/plages.txt gives cible={ecrit}, and the Pod cible has the address {ip or 'none'}. Expected its "
        "current address: a Pod only receives one once its network is set up.",
        fr=f"~/reseau/plages.txt donne cible={ecrit}, et le Pod cible a l'adresse {ip or 'aucune'}. Attendu son "
        "adresse actuelle : un Pod n'en reçoit une qu'une fois son réseau monté.",
    )


# ----------------------------------------------------------------------
# 3. Le worker est Ready.
# ----------------------------------------------------------------------
def test_le_worker_est_ready(host):
    noeud = _objet(host, f"get node {WORKER}")
    assert noeud is not None, message(
        en=f"The node {WORKER} is no longer part of the cluster: it had to be repaired, not removed.",
        fr=f"Le nœud {WORKER} ne fait plus partie du cluster : il fallait le réparer, pas le retirer.",
    )
    pret = next((c for c in noeud["status"].get("conditions") or [] if c.get("type") == "Ready"), {})
    assert pret.get("status") == "True", message(
        en=f"{WORKER} is not Ready: {pret.get('message', 'no message')}.",
        fr=f"{WORKER} n'est pas Ready : {pret.get('message', 'aucun message')}.",
    )


# ----------------------------------------------------------------------
# 4. cible tourne sur le worker.
# ----------------------------------------------------------------------
def test_cible_tourne_sur_le_worker(host):
    pod = _cible(host)
    assert pod is not None, message(
        en=f"No Pod cible in {NAMESPACE}.",
        fr=f"Aucun Pod cible dans {NAMESPACE}.",
    )
    noeud = pod["spec"].get("nodeName")
    phase = (pod.get("status") or {}).get("phase")
    assert noeud == WORKER and phase == "Running", message(
        en=f"cible is {phase} on {noeud}. Expected Running on {WORKER}: moving it to another node works around the "
        "failure without repairing it.",
        fr=f"cible est {phase} sur {noeud}. Attendu Running sur {WORKER} : le déplacer sur un autre nœud contourne la "
        "panne sans la réparer.",
    )


# ----------------------------------------------------------------------
# 5. sonde, sur le control plane, joint cible sur le worker.
# ----------------------------------------------------------------------
def test_sonde_joint_cible_depuis_l_autre_noeud(host):
    sonde = _objet(host, f"-n {NAMESPACE} get pod sonde") or {}
    pod = _cible(host) or {}
    ip = (pod.get("status") or {}).get("podIP")
    noeuds = ((sonde.get("spec") or {}).get("nodeName"), (pod.get("spec") or {}).get("nodeName"))
    corps = _kubectl(host, f"-n {NAMESPACE} exec sonde -- wget -qO- -T 3 http://{ip}/").stdout if ip else ""
    joint = "nginx" in corps
    assert noeuds == (PLAN, WORKER) and joint, message(
        en=f"sonde runs on {noeuds[0]}, cible on {noeuds[1]}, and sonde {'reaches' if joint else 'does not reach'} "
        f"cible by its address. Expected sonde on {PLAN} reaching cible on {WORKER}: a Pod joins a Pod of another "
        "node directly, without address translation.",
        fr=f"sonde tourne sur {noeuds[0]}, cible sur {noeuds[1]}, et sonde {'joint' if joint else 'ne joint pas'} "
        f"cible par son adresse. Attendu sonde sur {PLAN} qui joint cible sur {WORKER} : un Pod joint directement un "
        "Pod d'un autre nœud, sans traduction d'adresse.",
    )


# ----------------------------------------------------------------------
# 6. Le refus et le délai sont distingués.
# ----------------------------------------------------------------------
def test_le_refus_et_le_delai_sont_distingues(host):
    res = host.run(f"sudo cat {MEMOIRE}")
    assert res.rc == 0, message(
        en="The lab's draw cannot be read: replay the lab's preparation.",
        fr="Le tirage du lab est illisible : rejouez la préparation du lab.",
    )
    tirage = json.loads(res.stdout)
    attendu = {tirage["refus"]: "refus", tirage["delai"]: "delai"}
    ecrit = {k: v.lower().replace("é", "e") for k, v in _fichier(host, "verdicts.txt").items()}
    vu = {nom: ecrit.get(nom) for nom in attendu}
    assert vu == attendu, message(
        en=f"~/reseau/verdicts.txt gives {vu}. Each of the two Services fails in its own way: one refuses at once, "
        "the other leaves the connection waiting until the timeout. Time both to tell them apart.",
        fr=f"~/reseau/verdicts.txt donne {vu}. Chacun des deux Services échoue à sa façon : l'un refuse aussitôt, "
        "l'autre laisse la connexion attendre jusqu'au délai. Chronométrez-les pour les distinguer.",
    )
