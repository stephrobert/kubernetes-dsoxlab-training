"""test_functional.py : k8s-challenge-installer-un-cluster

Sept états, un par test, dans l'ordre de la fiche du challenge.

Les quatre premiers se lisent sur le cluster kubeadm (k8s-cp.lab) et sur le
worker k8s-w1.lab, que le setup a retiré du cluster et réinitialisé. Ils
reprennent les contrôles attestés de cka-joindre-un-noeud-kubeadm.

Les trois derniers se lisent sur l'hôte kind (k8s-kind.lab), où l'apprenant
crée le cluster ha à trois plans de contrôle. Le correcteur passe TOUJOURS par
l'adresse du répartiteur : le kubeconfig que rend `kind get kubeconfig`, dont
le port est vérifié comme celui que publie le conteneur ha-external-load-balancer.

Le dernier test arrête un plan de contrôle : il gèle son conteneur
(`docker pause`), interroge /readyz par le répartiteur, puis le dégèle, quoi
qu'il arrive. Il vient en dernier dans le fichier pour ne rien fausser des
autres lectures.

Les sept échouent sur l'état de départ : worker absent du cluster, swap actif
et inscrit dans fstab, containerd en cgroupfs, aucun Pod, aucun cluster ha.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
WORKER = "k8s-w1.lab"
NS = "installation"
POD = "temoin"
HA = "ha"
REPARTITEUR = f"{HA}-external-load-balancer"
KCFG = "/root/ha-correcteur.kubeconfig"
KHA = f"sudo kubectl --kubeconfig {KCFG} --request-timeout=10s"
ROLE_CP = "node-role.kubernetes.io/control-plane"
ETCD_CERTS = ("--endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt "
              "--cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt "
              "--key=/etc/kubernetes/pki/etcd/healthcheck-client.key")
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def cp():
    return lab_host("k8s-cp.lab")


@pytest.fixture(scope="module")
def w1():
    return lab_host(WORKER)


@pytest.fixture(scope="module")
def kind():
    return lab_host("k8s-kind.lab")


def _noeud(cp) -> dict | None:
    res = cp.run(f"{KUBECTL} get node {WORKER} -o json")
    return json.loads(res.stdout) if res.rc == 0 else None


def _pret(noeud: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (noeud.get("status") or {}).get("conditions") or [])


# ----------------------------------------------------------------------
# 1. Le worker réinitialisé est Ready, son kubelet en 1.37.
# ----------------------------------------------------------------------
def test_le_worker_reinitialise_est_ready_en_1_37(cp):
    noeud = _noeud(cp)
    assert noeud is not None, message(
        en=f"{WORKER} is not a node of the cluster: it has not joined yet.",
        fr=f"{WORKER} n'est pas un nœud du cluster : il n'a pas encore rejoint.",
    )
    assert _pret(noeud), message(
        en=f"{WORKER} has joined but is not Ready: its kubelet or its network does not work yet. "
        "`journalctl -u kubelet` on the worker says why.",
        fr=f"{WORKER} a rejoint mais n'est pas Ready : son kubelet ou son réseau ne fonctionne pas "
        "encore. `journalctl -u kubelet` sur le worker dit pourquoi.",
    )
    kubelet = noeud["status"].get("nodeInfo", {}).get("kubeletVersion", "")
    assert kubelet.startswith("v1.37."), message(
        en=f"The kubelet of {WORKER} reports {kubelet!r}, expected a 1.37 version, the cluster's.",
        fr=f"Le kubelet de {WORKER} annonce {kubelet!r}, attendu une version 1.37, celle du cluster.",
    )


# ----------------------------------------------------------------------
# 2. Le swap est coupé, et rien ne le rallumera au démarrage.
# ----------------------------------------------------------------------
def test_le_swap_est_coupe_et_le_reste_au_redemarrage(w1):
    actif = w1.check_output("swapon --noheadings --show=NAME").strip()
    fstab = w1.file("/etc/fstab").content_string.splitlines()
    inscrit = [ligne for ligne in fstab
               if ligne.strip() and not ligne.lstrip().startswith("#")
               and len(ligne.split()) >= 3 and ligne.split()[2] == "swap"]
    assert not actif and not inscrit, message(
        en=f"Swap on {WORKER}: active {actif.split() or 'none'}, still declared in /etc/fstab "
        f"{inscrit or 'nowhere'}. The kubelet refuses to run with swap, and an fstab entry turns it "
        "back on at the next boot.",
        fr=f"Swap sur {WORKER} : actif {actif.split() or 'aucun'}, encore déclaré dans /etc/fstab "
        f"{inscrit or 'nulle part'}. Le kubelet refuse de tourner avec du swap, et une ligne de fstab "
        "le rallume au prochain démarrage.",
    )


# ----------------------------------------------------------------------
# 3. containerd a CHARGÉ le pilote de cgroup systemd.
# ----------------------------------------------------------------------
def test_containerd_utilise_le_pilote_de_cgroup_systemd(w1):
    res = w1.run("sudo crictl info")
    assert res.rc == 0, message(
        en=f"crictl info does not answer on {WORKER}: containerd is not running.",
        fr=f"crictl info ne répond pas sur {WORKER} : containerd ne tourne pas.",
    )
    options = (((json.loads(res.stdout).get("config") or {}).get("containerd") or {})
               .get("runtimes", {}).get("runc", {}).get("options") or {})
    assert options.get("SystemdCgroup") is True, message(
        en=f"containerd on {WORKER} runs with SystemdCgroup = {options.get('SystemdCgroup')!r}. The "
        "kubelet uses the systemd cgroup driver: both must agree, and containerd only reads its "
        "configuration when it starts.",
        fr=f"containerd sur {WORKER} tourne avec SystemdCgroup = {options.get('SystemdCgroup')!r}. "
        "Le kubelet utilise le pilote de cgroup systemd : les deux doivent s'accorder, et containerd "
        "ne lit sa configuration qu'à son démarrage.",
    )


# ----------------------------------------------------------------------
# 4. Le Pod forcé sur le worker tourne.
# ----------------------------------------------------------------------
def test_un_pod_force_sur_le_worker_tourne(cp):
    res = cp.run(f"{KUBECTL} -n {NS} get pod {POD} -o json")
    assert res.rc == 0, message(
        en=f"No Pod {POD} in the {NS} namespace.",
        fr=f"Aucun Pod {POD} dans le namespace {NS}.",
    )
    pod = json.loads(res.stdout)
    place = pod["spec"].get("nodeName")
    assert place == WORKER, message(
        en=f"Pod {POD} is bound to {place!r}, not to {WORKER}. Its spec names the node itself, "
        "without going through the scheduler.",
        fr=f"Le Pod {POD} est lié à {place!r}, pas à {WORKER}. Sa spec nomme le nœud elle-même, "
        "sans passer par le scheduler.",
    )
    pret = (pod["status"].get("phase") == "Running"
            and all(s.get("ready") for s in pod["status"].get("containerStatuses") or [{}]))
    assert pret, message(
        en=f"Pod {POD} is on {WORKER} but in phase {pod['status'].get('phase')!r}, not running and "
        "ready. A Pod bound to a node that does not run it stays Pending.",
        fr=f"Le Pod {POD} est sur {WORKER} mais en phase {pod['status'].get('phase')!r}, pas en "
        "marche et prêt. Un Pod lié à un nœud qui ne le fait pas tourner reste Pending.",
    )


# ----------------------------------------------------------------------
# Le cluster ha, toujours lu par le répartiteur.
# ----------------------------------------------------------------------
def _repartiteur(kind) -> str:
    """Pose le kubeconfig du correcteur et rend l'adresse du répartiteur."""
    clusters = kind.run("sudo kind get clusters")
    assert clusters.rc == 0 and HA in clusters.stdout.split(), message(
        en=f"No kind cluster named {HA} on k8s-kind.lab.",
        fr=f"Aucun cluster kind nommé {HA} sur k8s-kind.lab.",
    )
    res = kind.run(f"sudo kind get kubeconfig --name {HA}")
    assert res.rc == 0, message(
        en=f"kind does not give the kubeconfig of cluster {HA}: {res.stderr.strip()[:200]}",
        fr=f"kind ne rend pas le kubeconfig du cluster {HA} : {res.stderr.strip()[:200]}",
    )
    serveur = ((yaml.safe_load(res.stdout) or {}).get("clusters") or [{}])[0].get("cluster", {}).get("server", "")
    publies = kind.run(f"sudo docker port {REPARTITEUR}")
    assert publies.rc == 0 and publies.stdout.strip(), message(
        en=f"Cluster {HA} has no load balancer ({REPARTITEUR} is missing): kind only puts one in "
        "front of the API servers when the cluster has several control-plane nodes.",
        fr=f"Le cluster {HA} n'a pas de répartiteur ({REPARTITEUR} est absent) : kind n'en place "
        "un devant les API servers que si le cluster compte plusieurs nœuds control-plane.",
    )
    ports = {ligne.rsplit(":", 1)[-1].strip() for ligne in publies.stdout.splitlines() if ":" in ligne}
    assert serveur.rsplit(":", 1)[-1] in ports, message(
        en=f"The kubeconfig of {HA} points to {serveur!r}, which is not the address published by "
        f"the load balancer {REPARTITEUR} ({sorted(ports)}).",
        fr=f"Le kubeconfig de {HA} vise {serveur!r}, qui n'est pas l'adresse que publie le "
        f"répartiteur {REPARTITEUR} ({sorted(ports)}).",
    )
    ecrit = kind.run(f"sudo sh -c 'kind get kubeconfig --name {HA} > {KCFG} && chmod 600 {KCFG}'")
    assert ecrit.rc == 0, message(
        en=f"Cannot write the grader's kubeconfig: {ecrit.stderr.strip()[:200]}",
        fr=f"Impossible d'écrire le kubeconfig du correcteur : {ecrit.stderr.strip()[:200]}",
    )
    return serveur


def _plans_de_controle(kind) -> list[dict]:
    res = kind.run(f"{KHA} get nodes -o json")
    if res.rc != 0:
        return []
    return [n for n in json.loads(res.stdout).get("items") or []
            if ROLE_CP in (n["metadata"].get("labels") or {})]


# ----------------------------------------------------------------------
# 5. Trois nœuds control-plane Ready, lus par le répartiteur.
# ----------------------------------------------------------------------
def test_trois_plans_de_controle_ready_par_le_repartiteur(kind):
    serveur = _repartiteur(kind)
    cps = _plans_de_controle(kind)
    # Trois plans de contrôle déclarés : on leur laisse le temps d'être Ready,
    # par exemple après qu'un check précédent en a gelé un.
    fin = time.monotonic() + ATTENTE
    while len(cps) == 3 and not all(_pret(n) for n in cps) and time.monotonic() < fin:
        time.sleep(PAS)
        cps = _plans_de_controle(kind)
    noms = {n["metadata"]["name"]: _pret(n) for n in cps}
    assert len(cps) == 3 and all(noms.values()), message(
        en=f"Through the load balancer ({serveur}), cluster {HA} shows these control-plane nodes, "
        f"with their Ready state: {noms or 'none'}. Expected three, all Ready.",
        fr=f"Par le répartiteur ({serveur}), le cluster {HA} montre ces nœuds control-plane, avec "
        f"leur état Ready : {noms or 'aucun'}. Attendu trois, tous Ready.",
    )


# ----------------------------------------------------------------------
# 6. etcd compte trois membres votants et sains.
# ----------------------------------------------------------------------
def test_etcd_compte_trois_membres_sains(kind):
    _repartiteur(kind)
    res = kind.run(f"{KHA} -n kube-system get pods -l component=etcd -o json")
    pods = [p["metadata"]["name"] for p in (json.loads(res.stdout).get("items") or [] if res.rc == 0 else [])
            if (p.get("status") or {}).get("phase") == "Running"]
    assert pods, message(
        en=f"No running etcd Pod in cluster {HA}.",
        fr=f"Aucun Pod etcd en marche dans le cluster {HA}.",
    )
    liste = kind.run(f"{KHA} -n kube-system exec {pods[0]} -- etcdctl {ETCD_CERTS} member list -w json")
    membres = json.loads(liste.stdout).get("members") or [] if liste.rc == 0 else []
    votants = [m.get("name") for m in membres if m.get("name") and not m.get("isLearner")]
    assert len(votants) == 3, message(
        en=f"etcd declares {len(membres)} member(s), {len(votants)} of them started and voting "
        f"({votants}). Expected three: one per control plane, stacked.",
        fr=f"etcd déclare {len(membres)} membre(s), dont {len(votants)} démarré(s) et votant(s) "
        f"({votants}). Attendu trois : un par plan de contrôle, empilés.",
    )
    sante = kind.run(f"{KHA} -n kube-system exec {pods[0]} -- etcdctl {ETCD_CERTS} "
                     "endpoint health --cluster -w json")
    try:
        points = json.loads(sante.stdout) if sante.stdout.strip() else []
    except json.JSONDecodeError:
        points = []
    sains = [p.get("endpoint") for p in points if p.get("health")]
    assert len(sains) == 3, message(
        en=f"etcd answers healthy on {len(sains)} endpoint(s) out of 3 ({sains}). A declared member "
        "is not a member that answers.",
        fr=f"etcd répond sain sur {len(sains)} point(s) d'accès sur 3 ({sains}). Un membre déclaré "
        "n'est pas un membre qui répond.",
    )


# ----------------------------------------------------------------------
# 7. L'API répond par le répartiteur quand un plan de contrôle est arrêté.
# ----------------------------------------------------------------------
def test_l_api_repond_par_le_repartiteur_apres_l_arret_d_un_plan_de_controle(kind):
    serveur = _repartiteur(kind)
    cps = sorted(n["metadata"]["name"] for n in _plans_de_controle(kind) if _pret(n))
    assert len(cps) == 3, message(
        en=f"Cluster {HA} has {len(cps)} Ready control plane(s) through {serveur}: the grader only "
        "stops one when three are up.",
        fr=f"Le cluster {HA} a {len(cps)} plan(s) de contrôle Ready par {serveur} : le correcteur "
        "n'en arrête un que si les trois sont debout.",
    )
    victime = cps[-1]
    gel = kind.run(f"sudo docker pause {victime}")
    assert gel.rc == 0, message(
        en=f"The grader cannot stop node {victime}: {gel.stderr.strip()[:200]}",
        fr=f"Le correcteur ne peut pas arrêter le nœud {victime} : {gel.stderr.strip()[:200]}",
    )
    reponses: list[str] = []
    try:
        # Le temps que le répartiteur constate la panne par ses contrôles de santé.
        time.sleep(20)
        suite = 0
        fin = time.monotonic() + 90
        while suite < 5 and time.monotonic() < fin:
            res = kind.run(f"sudo kubectl --kubeconfig {KCFG} --request-timeout=5s get --raw /readyz")
            ok = res.rc == 0 and res.stdout.strip() == "ok"
            reponses.append("ok" if ok else (res.stderr.strip().splitlines() or ["?"])[-1][:80])
            suite = suite + 1 if ok else 0
            time.sleep(2)
    finally:
        kind.run(f"sudo docker unpause {victime}")
    assert suite >= 5, message(
        en=f"With {victime} stopped, /readyz through the load balancer ({serveur}) did not answer "
        f"five times in a row within 90 s. Last answers: {reponses[-5:]}.",
        fr=f"Avec {victime} arrêté, /readyz par le répartiteur ({serveur}) n'a pas répondu cinq fois "
        f"de suite en 90 s. Dernières réponses : {reponses[-5:]}.",
    )
