"""test_functional.py : k8s-installer-cilium-sans-kube-proxy

Lab guidé de la leçon L1 du niveau 6 « Réseau avancé » (CKNE). Le setup laisse
trois nœuds prêts (kubelet, kubeadm et kubectl 1.37, containerd, helm) et AUCUN
cluster : net-cp.lab, net-w1.lab et net-w2.lab ont été remis à zéro. Chaque
test lit un état du cluster ou des nœuds, jamais une commande tapée, dans
l'ordre de la fiche :

1. le cluster est initialisé SANS kube-proxy : l'API répond, et kube-system ne
   porte ni DaemonSet ni ConfigMap kube-proxy ;
2. les deux workers sont joints et les trois nœuds sont Ready ;
3. Cilium 1.20.5 tourne sur chaque nœud et chaque agent annonce
   `KubeProxyReplacement: True` (cilium-dbg status) ;
4. aucun nœud ne porte de règle de kube-proxy (chaînes KUBE-SVC et
   KUBE-SERVICES d'iptables, table nftables kube-proxy), alors que le cluster
   sert ses Services ;
5. le Service web du namespace demo répond depuis un worker, et c'est Cilium
   qui le sert (il figure dans `cilium-dbg service list`) ;
6. l'IPAM est en mode cluster-pool sur le pool 10.244.0.0/16 : chaque
   CiliumNode y a son bloc, et les Pods de web y prennent leur adresse.

Les six échouent sur l'état de départ : aucun cluster ne répond. Le quatrième
n'est pas vrai avant le travail pour autant : il exige d'abord un cluster qui
sert des Services, puisqu'un nœud sans cluster n'a, lui non plus, aucune règle.
"""

from __future__ import annotations

import ipaddress
import json
import re
import time

import pytest

from conftest import lab_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
PLAN = "net-cp.lab"
WORKERS = ("net-w1.lab", "net-w2.lab")
NOEUDS = (PLAN, *WORKERS)
VERSION = "v1.20.5"
POOL = ipaddress.ip_network("10.244.0.0/16")
NS = "demo"
APPLI = "web"


@pytest.fixture(scope="module")
def cp():
    return lab_host(PLAN)


def _json(cp, args: str) -> dict | None:
    res = cp.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _api_repond(cp) -> bool:
    res = cp.run(f"{ADMIN} get --raw /readyz")
    return res.rc == 0 and res.stdout.strip() == "ok"


def _pret(pod: dict) -> bool:
    statuts = pod.get("status", {}).get("containerStatuses") or []
    return pod.get("status", {}).get("phase") == "Running" and bool(statuts) and all(
        s.get("ready") for s in statuts)


def _attendre(verifier, essais: int = 15, pause: int = 4):
    resultat = verifier()
    for _ in range(essais):
        if resultat[0]:
            break
        time.sleep(pause)
        resultat = verifier()
    return resultat


def _agents(cp) -> dict[str, str]:
    """Le Pod de l'agent Cilium de chaque nœud, nœud vers nom du Pod."""
    pods = (_json(cp, "-n kube-system get pods -l k8s-app=cilium") or {}).get("items", [])
    return {p["spec"].get("nodeName", ""): p["metadata"]["name"] for p in pods if _pret(p)}


def test_le_cluster_est_initialise_sans_kube_proxy(cp):
    api = _api_repond(cp)
    daemonset = cp.run(f"{ADMIN} -n kube-system get daemonset kube-proxy -o name")
    configmap = cp.run(f"{ADMIN} -n kube-system get configmap kube-proxy -o name")
    presents = [nom for nom, res in (("DaemonSet", daemonset), ("ConfigMap", configmap)) if res.rc == 0]
    assert api and not presents, message(
        en=(f"The API server of {PLAN} does not answer /readyz: no cluster is initialised yet."
            if not api else
            f"The cluster runs, but kube-system still holds kube-proxy ({', '.join(presents)}). "
            "kubeadm installs it unless its addon phase is skipped: kubeadm init "
            "--skip-phases=addon/kube-proxy."),
        fr=(f"L'API server de {PLAN} ne répond pas à /readyz : aucun cluster n'est encore initialisé."
            if not api else
            f"Le cluster tourne, mais kube-system porte encore kube-proxy ({', '.join(presents)}). "
            "kubeadm l'installe tant que sa phase d'addon n'est pas sautée : kubeadm init "
            "--skip-phases=addon/kube-proxy."),
    )


def test_les_trois_noeuds_sont_joints_et_ready(cp):
    def verifier():
        noeuds = (_json(cp, "get nodes") or {}).get("items", [])
        etats = {}
        for n in noeuds:
            conditions = n.get("status", {}).get("conditions") or []
            etats[n["metadata"]["name"]] = next(
                (c.get("status") for c in conditions if c.get("type") == "Ready"), None)
        return all(etats.get(nom) == "True" for nom in NOEUDS), etats

    ok, etats = _attendre(verifier)
    assert ok, message(
        en=f"Expected {', '.join(NOEUDS)} joined and Ready. Ready condition per node: {etats or 'no node'}. "
        "A worker missing from the list has not run kubeadm join; a node NotReady has no working CNI.",
        fr=f"Attendu : {', '.join(NOEUDS)} joints et Ready. Condition Ready par nœud : {etats or 'aucun nœud'}. "
        "Un worker absent de la liste n'a pas joué kubeadm join ; un nœud NotReady n'a pas de CNI qui marche.",
    )


def test_cilium_1_20_4_remplace_kube_proxy_sur_chaque_noeud(cp):
    daemonset = _json(cp, "-n kube-system get daemonset cilium") or {}
    conteneurs = daemonset.get("spec", {}).get("template", {}).get("spec", {}).get("containers") or []
    image = next((c.get("image", "") for c in conteneurs if c.get("name") == "cilium-agent"), "")
    agents = _attendre(lambda: (set(NOEUDS) <= set(_agents(cp)), _agents(cp)))[1]
    statuts = {}
    for noeud in NOEUDS:
        pod = agents.get(noeud)
        if not pod:
            statuts[noeud] = "no ready agent"
            continue
        sortie = cp.run(f"{ADMIN} -n kube-system exec {pod} -c cilium-agent -- cilium-dbg status").stdout
        ligne = re.search(r"^KubeProxyReplacement:\s*(\S+)", sortie, re.MULTILINE)
        statuts[noeud] = ligne.group(1) if ligne else "unreadable"
    assert f":{VERSION}" in image and all(v == "True" for v in statuts.values()), message(
        en=f"Expected the Cilium {VERSION} agent on every node with KubeProxyReplacement True. Agent image: "
        f"{image or 'no cilium DaemonSet'}; KubeProxyReplacement per node: {statuts}. The Helm value is "
        "kubeProxyReplacement=true, with k8sServiceHost and k8sServicePort pointing at the API server.",
        fr=f"Attendu : l'agent Cilium {VERSION} sur chaque nœud, avec KubeProxyReplacement True. Image de "
        f"l'agent : {image or 'aucun DaemonSet cilium'} ; KubeProxyReplacement par nœud : {statuts}. La "
        "valeur Helm est kubeProxyReplacement=true, avec k8sServiceHost et k8sServicePort qui visent "
        "l'API server.",
    )


def test_aucune_regle_kube_proxy_sur_les_noeuds(cp):
    # Le cluster doit d'abord servir ses Services : sans cluster, un nœud n'a
    # aucune règle non plus, et le test serait vrai avant le travail.
    service = _json(cp, "-n default get service kubernetes") or {}
    ip_service = service.get("spec", {}).get("clusterIP")
    trouvees = {}
    for noeud in NOEUDS:
        hote = lab_host(noeud)
        nat = hote.run("sudo iptables-save -t nat").stdout
        regles = [ligne for ligne in nat.splitlines() if "KUBE-SVC" in ligne or "KUBE-SERVICES" in ligne]
        tables = hote.run("sudo nft list tables 2>/dev/null").stdout
        if regles or "kube-proxy" in tables:
            trouvees[noeud] = len(regles) + (1 if "kube-proxy" in tables else 0)
    assert ip_service and not trouvees, message(
        en=("No cluster serves Services yet: the kubernetes Service is missing."
            if not ip_service else
            f"kube-proxy rules remain on {trouvees} (KUBE-SVC or KUBE-SERVICES chains, or a kube-proxy nftables "
            "table). kube-proxy ran on these nodes: delete it, then clean its rules with the filter the "
            "Cilium page gives (iptables-save | grep -v KUBE | iptables-restore)."),
        fr=("Aucun cluster ne sert encore de Services : le Service kubernetes est absent."
            if not ip_service else
            f"Des règles de kube-proxy restent sur {trouvees} (chaînes KUBE-SVC ou KUBE-SERVICES, ou table "
            "nftables kube-proxy). kube-proxy a tourné sur ces nœuds : supprimez-le, puis nettoyez ses règles "
            "avec le filtre que donne la page Cilium (iptables-save | grep -v KUBE | iptables-restore)."),
    )


def test_le_service_web_repond_par_cilium(cp):
    service = _json(cp, f"-n {NS} get service {APPLI}") or {}
    ip_service = service.get("spec", {}).get("clusterIP")
    ports = [p.get("port") for p in service.get("spec", {}).get("ports") or []]

    def verifier():
        if not ip_service or ip_service == "None":
            return False, "no Service"
        code = lab_host(WORKERS[0]).run(
            "curl -s -o /dev/null --max-time 5 -w '%{http_code}' http://" + f"{ip_service}:80/").stdout.strip()
        return code == "200", code

    repond, code = _attendre(verifier, essais=10, pause=3)
    agents = _agents(cp)
    liste = ""
    if agents:
        # `cilium-dbg service list` d'abord, la table BPF ensuite : la seconde
        # dit la même chose au niveau du datapath, si la première venait à
        # changer de forme d'une version à l'autre.
        exec_agent = f"{ADMIN} -n kube-system exec {next(iter(agents.values()))} -c cilium-agent --"
        res = cp.run(f"{exec_agent} cilium-dbg service list")
        liste = res.stdout if res.rc == 0 else cp.run(f"{exec_agent} cilium-dbg bpf lb list").stdout
    servi = bool(ip_service) and f"{ip_service}:80" in liste
    assert 80 in ports and repond and servi, message(
        en=(f"No ClusterIP Service {APPLI} on port 80 in namespace {NS}."
            if not ip_service or 80 not in ports else
            f"The Service {APPLI} ({ip_service}:80) answers HTTP {code or 'nothing'} from {WORKERS[0]}, and "
            f"{'appears' if servi else 'does not appear'} in cilium-dbg service list. Expected HTTP 200, "
            "served by Cilium."),
        fr=(f"Aucun Service ClusterIP {APPLI} sur le port 80 dans le namespace {NS}."
            if not ip_service or 80 not in ports else
            f"Le Service {APPLI} ({ip_service}:80) répond HTTP {code or 'rien'} depuis {WORKERS[0]}, et "
            f"{'figure' if servi else 'ne figure pas'} dans cilium-dbg service list. Attendu : HTTP 200, servi "
            "par Cilium."),
    )


def _dans_le_pool(adresse: str) -> bool:
    try:
        return ipaddress.ip_network(adresse, strict=False).subnet_of(POOL)
    except ValueError:
        return False


def test_les_pods_prennent_leur_adresse_dans_le_pool_cluster_pool(cp):
    config = (_json(cp, "-n kube-system get configmap cilium-config") or {}).get("data") or {}
    mode = config.get("ipam")
    blocs = {}
    for n in (_json(cp, "get ciliumnodes") or {}).get("items", []):
        blocs[n["metadata"]["name"]] = (n.get("spec", {}).get("ipam") or {}).get("podCIDRs") or []
    hors_pool = {nom: cidrs for nom, cidrs in blocs.items() if not cidrs or not all(_dans_le_pool(c) for c in cidrs)}
    pods = (_json(cp, f"-n {NS} get pods -l app={APPLI}") or {}).get("items", [])
    adresses = [p.get("status", {}).get("podIP", "") for p in pods if p.get("status", {}).get("podIP")]
    ok = (mode == "cluster-pool" and set(NOEUDS) <= set(blocs) and not hors_pool
          and adresses and all(_dans_le_pool(a) for a in adresses))
    assert ok, message(
        en=f"Expected IPAM mode cluster-pool on the pool {POOL}. ipam in cilium-config: {mode!r}; blocks per "
        f"CiliumNode: {blocs or 'none'}; addresses of the {APPLI} Pods: {adresses or 'none'}. The pool is set "
        "at install time (ipam.operator.clusterPoolIPv4PodCIDRList) and does not change afterwards.",
        fr=f"Attendu : l'IPAM en mode cluster-pool sur le pool {POOL}. ipam dans cilium-config : {mode!r} ; "
        f"blocs par CiliumNode : {blocs or 'aucun'} ; adresses des Pods {APPLI} : {adresses or 'aucune'}. Le "
        "pool se fixe à l'installation (ipam.operator.clusterPoolIPv4PodCIDRList) et ne change plus ensuite.",
    )
