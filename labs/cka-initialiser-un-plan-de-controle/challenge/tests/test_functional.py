"""test_functional.py : cka-initialiser-un-plan-de-controle

Le setup a remis les deux nœuds à zéro (kubeadm reset) et défait la
préparation du plan de contrôle. Chaque test lit un état sur k8s-cp.lab :

1. le cluster a été initialisé par le fichier ~/kubeadm/init.yaml : ce fichier
   déclare clusterName catalogue, et le ConfigMap kubeadm-config du cluster en
   marche porte ce nom et le podSubnet 10.244.0.0/16. Un init en ligne de
   commande, à côté d'un fichier jamais servi, ne passe pas ;
2. le kubeconfig de l'utilisateur répond sans sudo, et porte le certificat
   client de l'admin.conf de CE cluster ;
3. calico-node tourne et il est prêt sur k8s-cp.lab ;
4. le nœud est Ready et CoreDNS tourne ;
5. la préparation survit à un redémarrage : overlay et br_netfilter dans
   /etc/modules-load.d, net.ipv4.ip_forward = 1 actif ET écrit dans un fichier
   de sysctl, swap coupé et absent de fstab ;
6. kubeadm, kubelet et kubectl sont figés.

Les six échouent sur l'état de départ : aucun cluster, aucun kubeconfig,
ip_forward à 0, swap actif et inscrit dans fstab, paquets dégelés.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NOEUD = "k8s-cp.lab"
NOM = "catalogue"
PODS = "10.244.0.0/16"
PAQUETS = {"kubeadm", "kubelet", "kubectl"}


@pytest.fixture(scope="module")
def cp():
    return lab_host(NOEUD)


@pytest.fixture(scope="module")
def utilisateur(cp) -> str:
    # testinfra passe par sudo : $HOME vaudrait /root. L'utilisateur du lab est
    # celui que sudo a remplacé.
    return cp.check_output('echo "${SUDO_USER:-ansible}"').strip()


@pytest.fixture(scope="module")
def maison(cp, utilisateur) -> str:
    return cp.check_output(f"getent passwd {utilisateur} | cut -d: -f6").strip()


def _json(cp, args: str) -> dict | None:
    res = cp.run(f"{KUBECTL} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _pret(pod: dict) -> bool:
    return pod["status"].get("phase") == "Running" and bool(pod["status"].get("containerStatuses")) and all(
        s.get("ready") for s in pod["status"]["containerStatuses"])


def _attendre(verifier, essais: int = 15, pause: int = 4):
    resultat = verifier()
    for _ in range(essais):
        if resultat[0]:
            break
        time.sleep(pause)
        resultat = verifier()
    return resultat


def test_le_cluster_est_initialise_par_le_fichier_de_configuration(cp, maison):
    fichier = cp.file(f"{maison}/kubeadm/init.yaml")
    documents = []
    if fichier.exists:
        try:
            documents = [d for d in yaml.safe_load_all(fichier.content_string) if isinstance(d, dict)]
        except yaml.YAMLError:
            documents = []
    declare = next((d.get("clusterName") for d in documents if d.get("kind") == "ClusterConfiguration"), None)
    config = _json(cp, "-n kube-system get configmap kubeadm-config")
    en_marche = yaml.safe_load(config["data"]["ClusterConfiguration"]) if config else {}
    servi = {"clusterName": en_marche.get("clusterName"),
             "podSubnet": (en_marche.get("networking") or {}).get("podSubnet")}
    assert declare == NOM and servi == {"clusterName": NOM, "podSubnet": PODS}, message(
        en=f"{maison}/kubeadm/init.yaml declares clusterName {declare!r} in its ClusterConfiguration; the "
        f"running cluster reports {servi if config else 'no kubeadm-config ConfigMap'}. Expected: a cluster "
        f"named {NOM} with the pod network {PODS}, initialised from that file.",
        fr=f"{maison}/kubeadm/init.yaml déclare clusterName {declare!r} dans sa ClusterConfiguration ; le "
        f"cluster en marche annonce {servi if config else 'aucun ConfigMap kubeadm-config'}. Attendu : un "
        f"cluster nommé {NOM}, au réseau de Pods {PODS}, initialisé par ce fichier.",
    )


def test_le_kubeconfig_de_l_utilisateur_vise_le_nouveau_cluster(cp, utilisateur, maison):
    config = f"{maison}/.kube/config"
    # Joué EN TANT QUE l'utilisateur : un kubeconfig que lui seul ne peut pas
    # lire ne passe pas.
    en_tant_que = f"sudo -u {utilisateur} kubectl --kubeconfig {config}"
    res = cp.run(f"{en_tant_que} get --raw /readyz")
    assert res.rc == 0 and res.stdout.strip() == "ok", message(
        en=f"kubectl does not reach the API server with {config}, without sudo: "
        f"{(res.stdout + res.stderr).strip()[:160]}",
        fr=f"kubectl ne joint pas l'API server avec {config}, sans sudo : "
        f"{(res.stdout + res.stderr).strip()[:160]}",
    )
    chemin = "{.users[0].user.client-certificate-data}"
    sien = cp.check_output(f"{en_tant_que} config view --raw -o jsonpath='{chemin}'").strip()
    admin = cp.check_output(f"{KUBECTL} config view --raw -o jsonpath='{chemin}'").strip()
    assert sien and sien == admin, message(
        en=f"{config} works, but its client certificate is not the one in /etc/kubernetes/admin.conf of this "
        "cluster.",
        fr=f"{config} fonctionne, mais son certificat client n'est pas celui de /etc/kubernetes/admin.conf "
        "de ce cluster.",
    )


def test_calico_tourne_sur_le_plan_de_controle(cp):
    def verifier():
        pods = (_json(cp, "-n calico-system get pods -l k8s-app=calico-node") or {}).get("items", [])
        sur_le_noeud = [p for p in pods if p["spec"].get("nodeName") == NOEUD]
        return any(_pret(p) for p in sur_le_noeud), len(sur_le_noeud)

    pret, nombre = _attendre(verifier)
    assert pret, message(
        en=f"No calico-node Pod is running and ready on {NOEUD} ({nombre} placed there).",
        fr=f"Aucun Pod calico-node n'est en marche et prêt sur {NOEUD} ({nombre} placé(s) dessus).",
    )


def test_le_noeud_est_ready_et_coredns_tourne(cp):
    def verifier():
        noeud = _json(cp, f"get node {NOEUD}")
        conditions = (noeud or {}).get("status", {}).get("conditions") or []
        ready = next((c.get("status") for c in conditions if c.get("type") == "Ready"), None)
        pods = (_json(cp, "-n kube-system get pods -l k8s-app=kube-dns") or {}).get("items", [])
        coredns = sum(_pret(p) for p in pods)
        return ready == "True" and coredns > 0, ready, coredns

    ok, ready, coredns = _attendre(verifier)
    assert ok, message(
        en=f"Node {NOEUD}: Ready condition {ready!r}; CoreDNS Pods running and ready: {coredns}.",
        fr=f"Nœud {NOEUD} : condition Ready {ready!r} ; Pods CoreDNS en marche et prêts : {coredns}.",
    )


def _lignes_actives(cp, motif: str) -> list[str]:
    sortie = cp.run(f"sudo cat {motif} 2>/dev/null").stdout
    return [ligne.strip() for ligne in sortie.splitlines()
            if ligne.strip() and not ligne.lstrip().startswith(("#", ";"))]


def test_la_preparation_du_noeud_survit_au_redemarrage(cp):
    ecarts_en, ecarts_fr = [], []
    modules = set(_lignes_actives(cp, "/etc/modules-load.d/*.conf"))
    manquent = sorted({"overlay", "br_netfilter"} - modules)
    if manquent:
        ecarts_en.append(f"modules not loaded at boot by /etc/modules-load.d: {manquent}")
        ecarts_fr.append(f"modules non chargés au démarrage par /etc/modules-load.d : {manquent}")
    actif = cp.check_output("sysctl -n net.ipv4.ip_forward").strip()
    ecrit = [ligne for ligne in _lignes_actives(cp, "/etc/sysctl.conf /etc/sysctl.d/*.conf")
             if ligne.replace(" ", "").replace("\t", "") == "net.ipv4.ip_forward=1"]
    if actif != "1" or not ecrit:
        ecarts_en.append(f"net.ipv4.ip_forward is {actif} now, set to 1 in a sysctl file: {'yes' if ecrit else 'no'}")
        ecarts_fr.append(f"net.ipv4.ip_forward vaut {actif} maintenant, mis à 1 dans un fichier de sysctl : "
                         f"{'oui' if ecrit else 'non'}")
    swap = cp.check_output("swapon --noheadings --show=NAME").split()
    fstab = [ligne for ligne in _lignes_actives(cp, "/etc/fstab")
             if len(ligne.split()) >= 3 and ligne.split()[2] == "swap"]
    if swap or fstab:
        ecarts_en.append(f"swap active {swap or 'none'}, still declared in /etc/fstab {fstab or 'nowhere'}")
        ecarts_fr.append(f"swap actif {swap or 'aucun'}, encore déclaré dans /etc/fstab {fstab or 'nulle part'}")
    assert not ecarts_en, message(
        en=f"The preparation of {NOEUD} would not survive a reboot: " + "; ".join(ecarts_en) + ".",
        fr=f"La préparation de {NOEUD} ne survivrait pas à un redémarrage : " + " ; ".join(ecarts_fr) + ".",
    )


def test_les_paquets_sont_figes(cp):
    figes = set(cp.check_output("apt-mark showhold").split())
    manquent = sorted(PAQUETS - figes)
    assert not manquent, message(
        en=f"These packages are not held on {NOEUD}: {manquent}. An unattended upgrade would move them away "
        "from the cluster's version.",
        fr=f"Ces paquets ne sont pas figés sur {NOEUD} : {manquent}. Une mise à jour automatique les "
        "éloignerait de la version du cluster.",
    )
