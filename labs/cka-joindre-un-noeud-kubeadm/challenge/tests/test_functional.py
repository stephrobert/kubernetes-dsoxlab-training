"""test_functional.py : cka-joindre-un-noeud-kubeadm

Le setup a retiré k8s-w1.lab du cluster, l'a réinitialisé et a défait sa
préparation. Chaque test lit un état, sur le plan de contrôle ou sur le worker :

1. le worker est un nœud du cluster, Ready ;
2. son kubelet annonce la version de l'API server ;
3. le swap est coupé sur le worker, et aucune ligne active de fstab ne le
   rallumera au redémarrage ;
4. containerd tourne avec le pilote systemd : la valeur lue est celle que
   containerd a CHARGÉE (crictl info), une configuration éditée sans
   redémarrage ne passe pas ;
5. kubeadm, kubelet et kubectl sont figés ;
6. un Pod du namespace jonction tourne sur le worker.

Les six échouent sur l'état de départ : nœud absent, swap actif, pilote
cgroupfs, paquets dégelés, aucun Pod.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
WORKER = "k8s-w1.lab"
PAQUETS = {"kubeadm", "kubelet", "kubectl"}


@pytest.fixture(scope="module")
def cp():
    return lab_host("k8s-cp.lab")


@pytest.fixture(scope="module")
def w1():
    return lab_host(WORKER)


def _noeud(cp) -> dict | None:
    res = cp.run(f"{KUBECTL} get node {WORKER} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def test_le_worker_est_joint_et_ready(cp):
    noeud = _noeud(cp)
    assert noeud is not None, message(
        en=f"{WORKER} is not a node of the cluster.",
        fr=f"{WORKER} n'est pas un nœud du cluster.",
    )
    pret = next((c.get("status") for c in noeud["status"].get("conditions") or [] if c.get("type") == "Ready"), None)
    assert pret == "True", message(
        en=f"{WORKER} has joined, but its Ready condition is {pret!r}: the kubelet or the network of the node "
        "is not working yet.",
        fr=f"{WORKER} a rejoint le cluster, mais sa condition Ready vaut {pret!r} : le kubelet ou le réseau "
        "du nœud ne fonctionne pas encore.",
    )


def test_son_kubelet_annonce_la_version_du_cluster(cp):
    noeud = _noeud(cp)
    serveur = json.loads(cp.check_output(f"{KUBECTL} version -o json"))["serverVersion"]["gitVersion"]
    kubelet = ((noeud or {}).get("status") or {}).get("nodeInfo", {}).get("kubeletVersion")
    assert kubelet == serveur, message(
        en=f"The kubelet of {WORKER} reports {kubelet!r}, the API server {serveur!r}.",
        fr=f"Le kubelet de {WORKER} annonce {kubelet!r}, l'API server {serveur!r}.",
    )


def test_le_swap_est_coupe_durablement(w1):
    actif = w1.check_output("swapon --noheadings --show=NAME").strip()
    fstab = w1.file("/etc/fstab").content_string.splitlines()
    inscrit = [ligne for ligne in fstab
               if ligne.strip() and not ligne.lstrip().startswith("#")
               and len(ligne.split()) >= 3 and ligne.split()[2] == "swap"]
    assert not actif and not inscrit, message(
        en=f"Swap on {WORKER}: active {actif.split() or 'none'}, still declared in /etc/fstab {inscrit or 'nowhere'}. "
        "The kubelet refuses to run with swap, and an fstab entry turns it back on at the next boot.",
        fr=f"Swap sur {WORKER} : actif {actif.split() or 'aucun'}, encore déclaré dans /etc/fstab "
        f"{inscrit or 'nulle part'}. Le kubelet refuse de tourner avec du swap, et une ligne de fstab le "
        "rallume au prochain démarrage.",
    )


def test_containerd_utilise_le_pilote_systemd(w1):
    res = w1.run("sudo crictl info")
    assert res.rc == 0, message(
        en=f"crictl info does not answer on {WORKER}: containerd is not running.",
        fr=f"crictl info ne répond pas sur {WORKER} : containerd ne tourne pas.",
    )
    options = (((json.loads(res.stdout).get("config") or {}).get("containerd") or {})
               .get("runtimes", {}).get("runc", {}).get("options") or {})
    assert options.get("SystemdCgroup") is True, message(
        en=f"containerd on {WORKER} runs with SystemdCgroup = {options.get('SystemdCgroup')!r}. The kubelet "
        "uses the systemd cgroup driver: both must agree, and containerd only reads its configuration when it "
        "starts.",
        fr=f"containerd sur {WORKER} tourne avec SystemdCgroup = {options.get('SystemdCgroup')!r}. Le kubelet "
        "utilise le pilote de cgroup systemd : les deux doivent s'accorder, et containerd ne lit sa "
        "configuration qu'à son démarrage.",
    )


def test_les_paquets_sont_figes(w1):
    figes = set(w1.check_output("apt-mark showhold").split())
    manquent = sorted(PAQUETS - figes)
    assert not manquent, message(
        en=f"These packages are not held on {WORKER}: {manquent}. An unattended upgrade would move them away "
        "from the cluster's version.",
        fr=f"Ces paquets ne sont pas figés sur {WORKER} : {manquent}. Une mise à jour automatique les "
        "éloignerait de la version du cluster.",
    )


def test_un_pod_force_sur_le_worker_tourne(cp):
    res = cp.run(f"{KUBECTL} -n jonction get pods -o json")
    pods = json.loads(res.stdout).get("items", []) if res.rc == 0 else []
    sur_le_worker = [p for p in pods if p["spec"].get("nodeName") == WORKER]
    en_marche = [p["metadata"]["name"] for p in sur_le_worker
                 if p["status"].get("phase") == "Running"
                 and all(s.get("ready") for s in p["status"].get("containerStatuses") or [])]
    assert en_marche, message(
        en=f"No Pod of the jonction namespace runs on {WORKER} ({len(sur_le_worker)} placed there, none "
        "running and ready).",
        fr=f"Aucun Pod du namespace jonction ne tourne sur {WORKER} ({len(sur_le_worker)} placé(s) dessus, "
        "aucun en marche et prêt).",
    )
