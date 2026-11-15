"""test_functional.py : k8s-epreuve-administrer-un-cluster

L'épreuve du niveau 4. Dix-huit états, P01 à P18, un test chacun, dans l'ordre
de la fiche. Le cahier des charges ne nomme aucun type d'objet : les tests
retrouvent sur le cluster ce que l'apprenant a choisi, quand ce choix lui
revient (le budget de la vitrine, sa règle de répartition).

Où se lit chaque état :
  - le cluster kubeadm, depuis k8s-cp.lab (API, manifestes statiques,
    systemd, crictl, kubeadm, le dépôt git ~/epreuve/manifestes et le dossier
    ~/epreuve/constats) ;
  - le worker k8s-w1.lab, pour son swap ;
  - l'hôte kind k8s-kind.lab, pour la haute disponibilité (P03, P04), toujours
    par l'adresse du répartiteur que publie le conteneur ha-external-load-balancer.

Les contrôles repris d'un lab attesté le disent dans leur commentaire. Les
dix-huit échouent sur l'état hérité : API server sans réponse, kubelet du plan
de contrôle désactivé, worker hors du cluster et swap actif, boutique absente,
deux certificats à 20 jours, aucun cluster ha.
"""

from __future__ import annotations

import json
import math
import os
import time
import unicodedata

import pytest
import yaml

from conftest import lab_host, message

KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
CP = "k8s-cp.lab"
WORKER = "k8s-w1.lab"
NS = "boutique"
ETAT = "/var/lib/dsoxlab/k8s-epreuve-administrer-un-cluster.json"
VEILLE = "/var/backups/etcd/etcd-veille.db"
FRAICHE = "/var/backups/etcd/etcd-avant-restauration.db"
APRES = "apres-la-veille"
TEMOIN = "temoin-maintenance"
VERSION_CIBLE = "v1.37.0"
MANIFESTE_API = "/etc/kubernetes/manifests/kube-apiserver.yaml"
FICHIERS_DU_DEPOT = ("vitrine.yaml", "panier.yaml", "vitrine-pdb.yaml", "purge.yaml")
API_RETIREES = {"policy/v1beta1", "batch/v1beta1", "autoscaling/v2beta1", "autoscaling/v2beta2",
                "extensions/v1beta1", "networking.k8s.io/v1beta1", "apps/v1beta1", "apps/v1beta2",
                "flowcontrol.apiserver.k8s.io/v1beta1", "flowcontrol.apiserver.k8s.io/v1beta2",
                "flowcontrol.apiserver.k8s.io/v1beta3", "storage.k8s.io/v1beta1"}
CONF_PANIER = "/etc/panier/panier.conf"
TRENTE_JOURS = 30 * 24 * 3600
BUSYBOX = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
SONDE = "sonde-placement"
HOSTNAME = "kubernetes.io/hostname"

HA = "ha"
REPARTITEUR = f"{HA}-external-load-balancer"
KCFG = "/root/ha-correcteur.kubeconfig"
KHA = f"sudo kubectl --kubeconfig {KCFG} --request-timeout=10s"
ROLE_CP = "node-role.kubernetes.io/control-plane"

#: Ce qui dit qu'une chose manque ou est arrêtée, compacté (sans accent, espace
#: ni apostrophe) : « desactiv » couvre désactivé, « arret » arrêté.
DIT_ARRETE = ("disabled", "desactiv", "inactive", "inactif", "dead", "stopped", "arret", "stop",
              "notrunning", "nedemarre", "neconnaitpas")
DIT_LE_MANQUE = ("introuvable", "absent", "manqu", "missing", "notfound", "nosuchfile",
                 "nexistepas", "inexistant", "pastrouve", "cannotfind", "couldnotfind")


@pytest.fixture(scope="module")
def cp():
    return lab_host(CP)


@pytest.fixture(scope="module")
def w1():
    return lab_host(WORKER)


@pytest.fixture(scope="module")
def kind():
    return lab_host("k8s-kind.lab")


@pytest.fixture(scope="module")
def etat(cp) -> dict:
    res = cp.run(f"sudo cat {ETAT}")
    assert res.rc == 0, message(
        en=f"The state recorded by setup, {ETAT}, cannot be found: run dsoxlab run again.",
        fr=f"L'état noté par le setup, {ETAT}, est introuvable : rejouez dsoxlab run.",
    )
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# Outils communs.
# ----------------------------------------------------------------------
def _json(cp, args: str) -> dict | None:
    res = cp.run(f"{KUBECTL} {args} -o json --request-timeout=20s")
    return json.loads(res.stdout) if res.rc == 0 else None


def _api(cp) -> None:
    res = cp.run(f"{KUBECTL} get --raw /readyz --request-timeout=20s")
    assert res.rc == 0 and res.stdout.strip() == "ok", message(
        en="The API server of the kubeadm cluster does not answer: kubectl is blind, the node is not "
        f"(manifests, crictl, journalctl). {res.stderr.strip()[:160]}",
        fr="L'API server du cluster kubeadm ne répond pas : kubectl est aveugle, le nœud ne l'est pas "
        f"(manifestes, crictl, journalctl). {res.stderr.strip()[:160]}",
    )


def _pret(objet: dict) -> bool:
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in (objet.get("status") or {}).get("conditions") or [])


def _maison(cp) -> str:
    return cp.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()


def _compact(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if c.isalnum())


def _epoch(cp, date: str) -> int | None:
    res = cp.run(f"date -d '{date}' +%s")
    return int(res.stdout.strip()) if res.rc == 0 and res.stdout.strip().isdigit() else None


def _depuis_le_depot(cp, nom: str) -> str | None:
    """Le contenu de <nom> au dernier commit du dépôt, écrit dans un fichier root."""
    cible = f"/root/epreuve-correcteur-{nom}"
    res = cp.run(f"sudo sh -c \"git -c safe.directory='*' -C {_maison(cp)}/epreuve/manifestes "
                 f"show HEAD:{nom} > {cible}\"")
    return cible if res.rc == 0 else None


def _repertoire_d_etcd(cp) -> str | None:
    """Le hostPath monté sur le --data-dir de l'etcd EN MARCHE (repris de
    k8s-challenge-sauvegarder-et-restaurer, attesté)."""
    ids = cp.run("sudo crictl ps --name '^etcd$' -q").stdout.split()
    if not ids:
        return None
    res = cp.run(f"sudo crictl inspect {ids[0]}")
    if res.rc != 0:
        return None
    inspection = json.loads(res.stdout)
    config = (inspection.get("info") or {}).get("config") or {}
    arguments = list(config.get("args") or []) + list(config.get("command") or [])
    data_dir = next((a.split("=", 1)[1] for a in arguments if a.startswith("--data-dir=")), "/var/lib/etcd")
    montages = (inspection.get("status") or {}).get("mounts") or []
    return next((m.get("hostPath") for m in montages if m.get("containerPath") == data_dir), None)


def _restaure(cp, etat: dict) -> bool:
    source = _repertoire_d_etcd(cp)
    cree = cp.run(f"sudo stat -c %Y {source}/member") if source else None
    return bool(cree and cree.rc == 0 and int(cree.stdout.strip()) > int(etat["epoch"]))


def _garantis(pdb: dict, replicas: int) -> int | None:
    spec = pdb.get("spec") or {}
    for cle, sens in (("minAvailable", 1), ("maxUnavailable", -1)):
        v = spec.get(cle)
        if v is None:
            continue
        n = math.ceil(replicas * int(v[:-1]) / 100) if isinstance(v, str) and v.endswith("%") else int(v)
        return n if sens == 1 else replicas - n
    return None


def _correspond(selecteur: dict, etiquettes: dict) -> bool:
    if not selecteur:
        return False
    if any(etiquettes.get(k) != v for k, v in (selecteur.get("matchLabels") or {}).items()):
        return False
    for expr in selecteur.get("matchExpressions") or []:
        cle, op, valeurs = expr.get("key"), expr.get("operator"), expr.get("values") or []
        if op == "In" and etiquettes.get(cle) not in valeurs:
            return False
        if op == "NotIn" and etiquettes.get(cle) in valeurs:
            return False
        if op == "Exists" and cle not in etiquettes:
            return False
        if op == "DoesNotExist" and cle in etiquettes:
            return False
    return True


def _vitrine(cp) -> dict:
    dep = _json(cp, f"-n {NS} get deployment vitrine")
    assert dep is not None, message(
        en=f"The storefront (vitrine) is not in the {NS} namespace: the shop has not come back.",
        fr=f"La vitrine n'est pas dans le namespace {NS} : la boutique n'est pas revenue.",
    )
    return dep


def _pods(cp, selecteur: str) -> list[dict]:
    pods = (_json(cp, f"-n {NS} get pods -l {selecteur}") or {}).get("items") or []
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")]


# ----------------------------------------------------------------------
# P01 (critique) : le worker réinitialisé rejoint, Ready, kubelet 1.37.
# ----------------------------------------------------------------------
def test_p01_le_worker_reinitialise_est_ready_en_1_37(cp):
    _api(cp)
    noeud = _json(cp, f"get node {WORKER}")
    assert noeud is not None, message(
        en=f"{WORKER} is not a node of the cluster: it has not joined.",
        fr=f"{WORKER} n'est pas un nœud du cluster : il n'a pas rejoint.",
    )
    kubelet = noeud["status"].get("nodeInfo", {}).get("kubeletVersion", "")
    assert _pret(noeud) and kubelet.startswith("v1.37."), message(
        en=f"{WORKER} is {'Ready' if _pret(noeud) else 'not Ready'} and its kubelet reports {kubelet!r}; "
        "expected Ready with a 1.37 kubelet.",
        fr=f"{WORKER} est {'Ready' if _pret(noeud) else 'non Ready'} et son kubelet annonce {kubelet!r} ; "
        "attendu Ready avec un kubelet 1.37.",
    )


# ----------------------------------------------------------------------
# P02 : le swap est coupé sur le worker, et le reste au redémarrage.
# Repris de cka-joindre-un-noeud-kubeadm (attesté).
# ----------------------------------------------------------------------
def test_p02_le_swap_est_coupe_et_le_reste_au_redemarrage(w1):
    actif = w1.check_output("swapon --noheadings --show=NAME").strip()
    fstab = w1.file("/etc/fstab").content_string.splitlines()
    inscrit = [ligne for ligne in fstab
               if ligne.strip() and not ligne.lstrip().startswith("#")
               and len(ligne.split()) >= 3 and ligne.split()[2] == "swap"]
    assert not actif and not inscrit, message(
        en=f"Swap on {WORKER}: active {actif.split() or 'none'}, still declared in /etc/fstab "
        f"{inscrit or 'nowhere'}.",
        fr=f"Swap sur {WORKER} : actif {actif.split() or 'aucun'}, encore déclaré dans /etc/fstab "
        f"{inscrit or 'nulle part'}.",
    )


# ----------------------------------------------------------------------
# P03 et P04 : la haute disponibilité, par le répartiteur.
# Repris de k8s-challenge-installer-un-cluster.
# ----------------------------------------------------------------------
def _repartiteur(kind) -> str:
    clusters = kind.run("sudo kind get clusters")
    assert clusters.rc == 0 and HA in clusters.stdout.split(), message(
        en=f"No kind cluster named {HA} on k8s-kind.lab.",
        fr=f"Aucun cluster kind nommé {HA} sur k8s-kind.lab.",
    )
    res = kind.run(f"sudo kind get kubeconfig --name {HA}")
    assert res.rc == 0, message(
        en=f"kind does not give the kubeconfig of cluster {HA}.",
        fr=f"kind ne rend pas le kubeconfig du cluster {HA}.",
    )
    serveur = ((yaml.safe_load(res.stdout) or {}).get("clusters") or [{}])[0].get("cluster", {}).get("server", "")
    publies = kind.run(f"sudo docker port {REPARTITEUR}")
    assert publies.rc == 0 and publies.stdout.strip(), message(
        en=f"Cluster {HA} has no load balancer ({REPARTITEUR} is missing): there is one only in front "
        "of several control planes.",
        fr=f"Le cluster {HA} n'a pas de répartiteur ({REPARTITEUR} est absent) : il n'y en a un que "
        "devant plusieurs plans de contrôle.",
    )
    ports = {ligne.rsplit(":", 1)[-1].strip() for ligne in publies.stdout.splitlines() if ":" in ligne}
    assert serveur.rsplit(":", 1)[-1] in ports, message(
        en=f"The kubeconfig of {HA} points to {serveur!r}, not to the load balancer ({sorted(ports)}).",
        fr=f"Le kubeconfig de {HA} vise {serveur!r}, pas le répartiteur ({sorted(ports)}).",
    )
    ecrit = kind.run(f"sudo sh -c 'kind get kubeconfig --name {HA} > {KCFG} && chmod 600 {KCFG}'")
    assert ecrit.rc == 0, message(
        en="Cannot write the grader's kubeconfig.",
        fr="Impossible d'écrire le kubeconfig du correcteur.",
    )
    return serveur


def _plans_de_controle(kind) -> list[dict]:
    res = kind.run(f"{KHA} get nodes -o json")
    if res.rc != 0:
        return []
    return [n for n in json.loads(res.stdout).get("items") or []
            if ROLE_CP in (n["metadata"].get("labels") or {})]


def test_p03_trois_plans_de_controle_ready_par_le_repartiteur(kind):
    serveur = _repartiteur(kind)
    cps = _plans_de_controle(kind)
    fin = time.monotonic() + 120
    while len(cps) == 3 and not all(_pret(n) for n in cps) and time.monotonic() < fin:
        time.sleep(5)
        cps = _plans_de_controle(kind)
    noms = {n["metadata"]["name"]: _pret(n) for n in cps}
    assert len(cps) == 3 and all(noms.values()), message(
        en=f"Through the load balancer ({serveur}), cluster {HA} shows these control-plane nodes: "
        f"{noms or 'none'}. Expected three, all Ready.",
        fr=f"Par le répartiteur ({serveur}), le cluster {HA} montre ces nœuds control-plane : "
        f"{noms or 'aucun'}. Attendu trois, tous Ready.",
    )


def test_p04_l_api_repond_par_le_repartiteur_apres_l_arret_d_un_plan_de_controle(kind):
    serveur = _repartiteur(kind)
    cps = sorted(n["metadata"]["name"] for n in _plans_de_controle(kind) if _pret(n))
    assert len(cps) == 3, message(
        en=f"Cluster {HA} has {len(cps)} Ready control plane(s): the grader only stops one when three "
        "are up.",
        fr=f"Le cluster {HA} a {len(cps)} plan(s) de contrôle Ready : le correcteur n'en arrête un que "
        "si les trois sont debout.",
    )
    victime = cps[-1]
    gel = kind.run(f"sudo docker pause {victime}")
    assert gel.rc == 0, message(
        en=f"The grader cannot stop node {victime}.",
        fr=f"Le correcteur ne peut pas arrêter le nœud {victime}.",
    )
    reponses: list[str] = []
    suite = 0
    try:
        time.sleep(20)
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
        en=f"With {victime} stopped, /readyz through the load balancer ({serveur}) did not answer five "
        f"times in a row within 90 s. Last answers: {reponses[-5:]}.",
        fr=f"Avec {victime} arrêté, /readyz par le répartiteur ({serveur}) n'a pas répondu cinq fois de "
        f"suite en 90 s. Dernières réponses : {reponses[-5:]}.",
    )


# ----------------------------------------------------------------------
# P05 : une sauvegarde fraîche, vérifiée, plus récente que la veille.
# Repris de k8s-challenge-sauvegarder-et-restaurer (attesté).
# ----------------------------------------------------------------------
def test_p05_une_sauvegarde_fraiche_verifiee_plus_recente_que_la_veille(cp, etat):
    res = cp.run(f"sudo etcdutl snapshot status {FRAICHE} -w json")
    assert res.rc == 0, message(
        en=f"No readable etcd snapshot at {FRAICHE}. You never restore without first backing up what "
        "you are about to overwrite.",
        fr=f"Aucun instantané etcd lisible dans {FRAICHE}. On ne restaure jamais sans avoir d'abord "
        "sauvegardé ce qu'on s'apprête à écraser.",
    )
    revision = json.loads(res.stdout).get("revision", 0)
    assert revision > etat["revision_veille"] and revision >= etat["revision"], message(
        en=f"The snapshot is at revision {revision}; the previous day's backup is at "
        f"{etat['revision_veille']}, the cluster was at {etat['revision']} when the test started. A copy "
        "of the old backup photographs nothing new.",
        fr=f"L'instantané est à la révision {revision} ; la sauvegarde de la veille est à "
        f"{etat['revision_veille']}, le cluster en était à {etat['revision']} au début de l'épreuve. Une "
        "copie de l'ancienne sauvegarde ne photographie rien de neuf.",
    )
    source = _repertoire_d_etcd(cp)
    restaure = cp.run(f"sudo stat -c %Y {source}/member") if source else None
    if restaure and restaure.rc == 0 and int(restaure.stdout.strip()) > int(etat["epoch"]):
        prise = int(cp.check_output(f"sudo stat -c %Y {FRAICHE}").strip())
        assert prise <= int(restaure.stdout.strip()), message(
            en="The fresh backup was taken after the restore: it photographs the restored state, not the "
            "one that was overwritten.",
            fr="La sauvegarde fraîche a été prise après la restauration : elle photographie l'état "
            "restauré, pas celui qui a été écrasé.",
        )


# ----------------------------------------------------------------------
# P06 (critique) : la boutique est revenue avec ses UID d'origine.
# ----------------------------------------------------------------------
def test_p06_la_boutique_est_revenue_avec_ses_uid_d_origine(cp, etat):
    _api(cp)
    trouves = {
        "namespace/boutique": ((_json(cp, f"get namespace {NS}") or {}).get("metadata") or {}).get("uid"),
        "vitrine": ((_json(cp, f"-n {NS} get deployment vitrine") or {}).get("metadata") or {}).get("uid"),
        "panier": ((_json(cp, f"-n {NS} get deployment panier") or {}).get("metadata") or {}).get("uid"),
    }
    attendus = {"namespace/boutique": etat["ns_uid"], "vitrine": etat["vitrine_uid"], "panier": etat["panier_uid"]}
    ecarts = {k: v for k, v in trouves.items() if v != attendus[k]}
    assert not ecarts, message(
        en=f"These objects are missing or do not carry their original UID: {ecarts}. A restore brings "
        "back the same objects; recreating them from the manifests gives new ones.",
        fr=f"Ces objets manquent ou ne portent pas leur UID d'origine : {ecarts}. Une restauration "
        "ramène les mêmes objets ; les recréer depuis les manifestes en donne de nouveaux.",
    )


# ----------------------------------------------------------------------
# P07 : l'objet créé après la veille n'existe plus, les nœuds sont Ready.
# ----------------------------------------------------------------------
def test_p07_l_objet_cree_apres_la_veille_n_existe_plus_et_les_noeuds_sont_ready(cp, etat):
    _api(cp)
    present = _json(cp, f"-n default get configmap {APRES}") is not None
    restaure = _restaure(cp, etat)
    etat_en = "still exists" if present else "is gone, but etcd was not restored"
    etat_fr = "existe encore" if present else "a disparu, mais etcd n'a pas été restauré"
    assert restaure and not present, message(
        en=f"{APRES} {etat_en}: written after the previous day's backup, it disappears with the restore "
        "of that backup.",
        fr=f"{APRES} {etat_fr} : écrit après la sauvegarde de la veille, il disparaît avec la "
        "restauration de cette sauvegarde.",
    )
    pas_prets: list[str] = []
    for _ in range(18):
        noeuds = (_json(cp, "get nodes") or {}).get("items") or []
        pas_prets = [n["metadata"]["name"] for n in noeuds if not _pret(n)]
        if noeuds and not pas_prets:
            break
        time.sleep(5)
    assert not pas_prets, message(
        en=f"After the restore, these nodes are not Ready: {pas_prets}.",
        fr=f"Après la restauration, ces nœuds ne sont pas Ready : {pas_prets}.",
    )


# ----------------------------------------------------------------------
# P08 : les manifestes en API supprimée sont migrés et s'appliquent.
# ----------------------------------------------------------------------
def test_p08_les_manifestes_sont_migres_et_s_appliquent(cp):
    _api(cp)
    refuses: dict[str, str] = {}
    for nom in FICHIERS_DU_DEPOT:
        fichier = _depuis_le_depot(cp, nom)
        if fichier is None:
            refuses[nom] = message(en="missing from the last commit: migrate it, do not remove it",
                                   fr="absent du dernier commit : migrez-le, ne le retirez pas")
            continue
        contenu = cp.run(f"sudo cat {fichier}").stdout
        try:
            versions = {d.get("apiVersion") for d in yaml.safe_load_all(contenu) if d}
        except yaml.YAMLError:
            versions = set()
        if versions & API_RETIREES:
            refuses[nom] = message(en=f"still uses {sorted(versions & API_RETIREES)}",
                                   fr=f"emploie encore {sorted(versions & API_RETIREES)}")
            continue
        essai = cp.run(f"{KUBECTL} apply --dry-run=server -f {fichier}")
        if essai.rc != 0:
            refuses[nom] = (essai.stderr.strip().splitlines() or ["?"])[-1][:160]
    assert not refuses, message(
        en=f"In the last commit of ~/epreuve/manifestes, these manifests are not accepted by the API "
        f"server: {refuses}.",
        fr=f"Au dernier commit de ~/epreuve/manifestes, ces manifestes ne sont pas acceptés par l'API "
        f"server : {refuses}.",
    )


# ----------------------------------------------------------------------
# P09 (critique) : la version cible partout, aucun nœud inordonnançable,
# la vitrine garde ses réplicas prêts. Repris de cka-kubeadm-upgrade.
# ----------------------------------------------------------------------
def test_p09_cluster_monte_en_1_37_0_sans_perdre_la_boutique(cp):
    _api(cp)
    version = cp.run(f"{KUBECTL} version -o json --request-timeout=30s")
    serveur = (json.loads(version.stdout).get("serverVersion") or {}).get("gitVersion", "") if version.rc == 0 else ""
    assert serveur.split("+")[0] == VERSION_CIBLE, message(
        en=f"The API server reports {serveur!r}, not {VERSION_CIBLE}.",
        fr=f"L'API server annonce {serveur!r}, et non {VERSION_CIBLE}.",
    )
    noeuds = (_json(cp, "get nodes") or {}).get("items") or []
    en_retard = {n["metadata"]["name"]: n["status"]["nodeInfo"]["kubeletVersion"] for n in noeuds
                 if n["status"]["nodeInfo"]["kubeletVersion"].split("+")[0] != VERSION_CIBLE}
    vides = [n["metadata"]["name"] for n in noeuds if n["spec"].get("unschedulable")]
    assert len(noeuds) >= 2 and not en_retard and not vides, message(
        en=f"{len(noeuds)} node(s); still on another version: {en_retard or 'none'}; left unschedulable: "
        f"{vides or 'none'}. Every node goes up, and goes back into service.",
        fr=f"{len(noeuds)} nœud(s) ; encore sur une autre version : {en_retard or 'aucun'} ; restés "
        f"inordonnançables : {vides or 'aucun'}. Chaque nœud monte, et revient en service.",
    )
    pretes, voulues = 0, -1
    for _ in range(18):
        dep = _vitrine(cp)
        voulues = dep["spec"].get("replicas", 1)
        pretes = (dep.get("status") or {}).get("readyReplicas") or 0
        if pretes == voulues:
            break
        time.sleep(5)
    assert pretes == voulues, message(
        en=f"The storefront has {pretes} ready replica(s) out of {voulues}.",
        fr=f"La vitrine a {pretes} réplica(s) prêt(s) sur {voulues}.",
    )


# ----------------------------------------------------------------------
# P10 : un budget cible les Pods de la vitrine et garantit le minimum.
# ----------------------------------------------------------------------
def test_p10_un_budget_protege_la_vitrine(cp):
    _api(cp)
    dep = _vitrine(cp)
    replicas = dep["spec"].get("replicas", 1)
    etiquettes = (dep["spec"]["template"]["metadata"].get("labels") or {})
    budgets = (_json(cp, f"-n {NS} get pdb") or {}).get("items") or []
    siens = [b for b in budgets if _correspond((b.get("spec") or {}).get("selector") or {}, etiquettes)]
    assert siens, message(
        en="Nothing limits voluntary disruptions of the storefront: no budget in the shop's namespace "
        "targets its Pods.",
        fr="Rien ne limite les perturbations volontaires de la vitrine : aucun budget du namespace de la "
        "boutique ne vise ses Pods.",
    )
    garantis = {b["metadata"]["name"]: _garantis(b, replicas) for b in siens}
    bons = [n for n, g in garantis.items() if g is not None and 1 <= g < replicas]
    assert bons, message(
        en=f"With {replicas} replicas, these budgets keep {garantis} Pod(s) available. Expected at least "
        "one, and fewer than all of them, otherwise no node can ever be drained.",
        fr=f"Avec {replicas} réplicas, ces budgets gardent {garantis} Pod(s) disponible(s). Attendu au "
        "moins un, et moins que tous, sinon aucun nœud ne pourra jamais être vidé.",
    )


# ----------------------------------------------------------------------
# P11 : le worker a été évacué sans couper la boutique, puis remis en service.
# ----------------------------------------------------------------------
def test_p11_le_worker_a_ete_evacue_puis_remis_en_service(cp):
    _api(cp)
    noeud = _json(cp, f"get node {WORKER}") or {}
    assert noeud and _pret(noeud) and not noeud["spec"].get("unschedulable", False), message(
        en=f"{WORKER} is not a Ready node back in scheduling.",
        fr=f"{WORKER} n'est pas un nœud Ready revenu dans le scheduling.",
    )
    temoin = _json(cp, f"-n {NS} get pod {TEMOIN}")
    assert temoin is None or temoin["metadata"].get("deletionTimestamp"), message(
        en=f"Pod {TEMOIN}, bound to the worker with no controller, is still there: the worker was never "
        "emptied.",
        fr=f"Le Pod {TEMOIN}, lié au worker sans contrôleur, est toujours là : le worker n'a jamais été "
        "vidé.",
    )
    dep = _vitrine(cp)
    pretes = (dep.get("status") or {}).get("readyReplicas") or 0
    assert pretes >= 1, message(
        en="The storefront has no ready replica: the shop is down.",
        fr="La vitrine n'a aucun réplica prêt : la boutique est coupée.",
    )
    sonde = json.dumps({
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": SONDE, "namespace": NS},
        "spec": {"nodeSelector": {HOSTNAME: WORKER}, "restartPolicy": "Never",
                 "containers": [{"name": "sonde", "image": BUSYBOX, "command": ["sleep", "60"]}]},
    })
    cp.run(f"{KUBECTL} -n {NS} delete pod {SONDE} --ignore-not-found --wait=true")
    try:
        cree = cp.run(f"echo '{sonde}' | {KUBECTL} apply -f -")
        assert cree.rc == 0, message(
            en=f"The grader cannot create its probe Pod: {cree.stderr.strip()[:200]}",
            fr=f"Le correcteur ne peut pas créer son Pod sonde : {cree.stderr.strip()[:200]}",
        )
        attente = cp.run(f"{KUBECTL} -n {NS} wait --for=condition=Ready pod/{SONDE} --timeout=90s")
        assert attente.rc == 0, message(
            en=f"A Pod the scheduler must place on {WORKER} does not start there within 90 s: the worker "
            "does not accept new Pods.",
            fr=f"Un Pod que le scheduler doit placer sur {WORKER} n'y démarre pas en 90 s : le worker "
            "n'accepte pas de nouveaux Pods.",
        )
    finally:
        cp.run(f"{KUBECTL} -n {NS} delete pod {SONDE} --ignore-not-found --wait=false")


# ----------------------------------------------------------------------
# P12 (critique) : le nœud NotReady est Ready, son kubelet survivra au
# redémarrage. Repris de cka-troubleshoot-node-notready.
# ----------------------------------------------------------------------
def test_p12_le_noeud_notready_est_ready_et_son_kubelet_survivra_au_redemarrage(cp):
    active = cp.run("systemctl is-active kubelet").stdout.strip()
    activee = cp.run("systemctl is-enabled kubelet").stdout.strip()
    assert active == "active" and activee == "enabled", message(
        en=f"The kubelet of {CP} is {active!r} and {activee!r} at boot: expected running, and enabled so "
        "that it starts again after a reboot.",
        fr=f"Le kubelet de {CP} est {active!r} et {activee!r} au démarrage : attendu en marche, et activé "
        "pour repartir après un redémarrage.",
    )
    _api(cp)
    noeud = _json(cp, f"get node {CP}") or {}
    assert _pret(noeud), message(
        en=f"{CP} is not Ready.",
        fr=f"{CP} n'est pas Ready.",
    )


# ----------------------------------------------------------------------
# P13 (critique) : l'API server répond et autorise toujours Node,RBAC.
# Repris de cka-troubleshoot-apiserver (attesté).
# ----------------------------------------------------------------------
def test_p13_l_api_server_repond_et_autorise_toujours_node_rbac(cp):
    manifeste = cp.run(f"sudo cat {MANIFESTE_API}")
    assert manifeste.rc == 0, message(
        en=f"Cannot read {MANIFESTE_API}.",
        fr=f"Impossible de lire {MANIFESTE_API}.",
    )
    assert "--authorization-modes=" not in manifeste.stdout, message(
        en="The API server manifest still carries a flag the API server does not know, and it exits at "
        "startup. Compare it letter by letter with the documented flag.",
        fr="Le manifeste de l'API server porte encore un flag que l'API server ne connaît pas, et il sort "
        "au démarrage. Comparez-le lettre par lettre au flag documenté.",
    )
    assert "--authorization-mode=Node,RBAC" in manifeste.stdout, message(
        en="The manifest no longer declares --authorization-mode=Node,RBAC: removing the line restarts "
        "the API server, but without authorization it is an open door.",
        fr="Le manifeste ne déclare plus --authorization-mode=Node,RBAC : retirer la ligne fait "
        "redémarrer l'API server, mais sans autorisation c'est une porte ouverte.",
    )
    sante = cp.run(f"{KUBECTL} get --raw /healthz --request-timeout=20s")
    assert sante.rc == 0 and sante.stdout.strip() == "ok", message(
        en="The API server does not answer /healthz.",
        fr="L'API server ne répond pas à /healthz.",
    )


# ----------------------------------------------------------------------
# P14 : panier a ses réplicas disponibles, ne redémarre plus, et lit sa
# configuration au bon endroit.
# ----------------------------------------------------------------------
def test_p14_panier_est_disponible_stable_et_lit_sa_configuration(cp):
    _api(cp)
    dep = _json(cp, f"-n {NS} get deployment panier")
    assert dep is not None, message(
        en="The panier component is not in the shop's namespace.",
        fr="Le composant panier n'est pas dans le namespace de la boutique.",
    )
    voulues, dispo = dep["spec"].get("replicas", 1), 0
    for _ in range(18):
        dep = _json(cp, f"-n {NS} get deployment panier") or dep
        dispo = (dep.get("status") or {}).get("availableReplicas") or 0
        if dispo == voulues:
            break
        time.sleep(5)
    assert dispo == voulues, message(
        en=f"panier has {dispo} available replica(s) out of {voulues}.",
        fr=f"panier a {dispo} réplica(s) disponible(s) sur {voulues}.",
    )

    def compteurs() -> dict[str, int]:
        return {p["metadata"]["name"]: sum(c.get("restartCount", 0) for c in p["status"].get("containerStatuses") or [])
                for p in _pods(cp, "app=panier") if p["status"].get("phase") == "Running"}

    avant = compteurs()
    time.sleep(20)
    apres = compteurs()
    relances = sorted(n for n in avant if n in apres and apres[n] > avant[n])
    assert avant and not relances, message(
        en=f"panier still restarts: {relances or 'no running Pod'} within 20 s.",
        fr=f"panier redémarre encore : {relances or 'aucun Pod en marche'} en 20 s.",
    )
    pod = sorted(apres or avant)[0]
    lu = cp.run(f"{KUBECTL} -n {NS} exec {pod} -- cat {CONF_PANIER}")
    assert lu.rc == 0 and "devise=EUR" in lu.stdout, message(
        en=f"Inside {pod}, {CONF_PANIER} does not hold panier's configuration: the component reads it "
        "there, and nowhere else.",
        fr=f"Dans {pod}, {CONF_PANIER} ne porte pas la configuration de panier : le composant la lit là, "
        "et nulle part ailleurs.",
    )


# ----------------------------------------------------------------------
# P15 : la cause de chaque panne est consignée avant la réparation.
# ----------------------------------------------------------------------
def test_p15_la_cause_de_chaque_panne_est_consignee_avant_la_reparation(cp):
    dossier = f"{_maison(cp)}/epreuve/constats"
    fautes: list[str] = []
    textes: dict[str, str] = {}
    dates: dict[str, int] = {}
    for nom in ("kubelet", "apiserver", "panier"):
        f = cp.file(f"{dossier}/{nom}.txt")
        if not f.exists:
            fautes.append(f"{nom}.txt absent")
            continue
        textes[nom] = _compact(f.content_string)
        dates[nom] = int(cp.check_output(f"stat -c %Y {dossier}/{nom}.txt").strip())
    if "kubelet" in textes and not ("kubelet" in textes["kubelet"]
                                    and any(m in textes["kubelet"] for m in DIT_ARRETE)):
        fautes.append("kubelet.txt ne dit pas que le kubelet était arrêté ou désactivé")
    if "apiserver" in textes and "authorizationmodes" not in textes["apiserver"]:
        fautes.append("apiserver.txt ne nomme pas le flag fautif")
    if "panier" in textes and not ("etcpanier" in textes["panier"]
                                   and any(m in textes["panier"] for m in DIT_LE_MANQUE)):
        fautes.append("panier.txt ne dit pas que /etc/panier/panier.conf manque")

    # Avant la réparation : chaque constat est plus ancien que ce qui tourne
    # aujourd'hui, réparé.
    if "kubelet" in dates:
        entre = cp.run("systemctl show kubelet -p ActiveEnterTimestamp --value").stdout.strip()
        depuis = _epoch(cp, entre) if entre else None
        if depuis is None or dates["kubelet"] > depuis:
            fautes.append("kubelet.txt écrit après le démarrage du kubelet réparé")
    if "apiserver" in dates:
        ids = cp.run("sudo crictl ps --name '^kube-apiserver$' -q").stdout.split()
        inspection = cp.run(f"sudo crictl inspect {ids[0]}") if ids else None
        demarre = ((json.loads(inspection.stdout).get("status") or {}).get("startedAt")
                   if inspection is not None and inspection.rc == 0 else None)
        depuis = _epoch(cp, demarre) if demarre else None
        if depuis is None or dates["apiserver"] > depuis:
            fautes.append("apiserver.txt écrit après le démarrage de l'API server réparé")
    if "panier" in dates:
        departs = [((c.get("state") or {}).get("running") or {}).get("startedAt")
                   for p in _pods(cp, "app=panier") for c in p["status"].get("containerStatuses") or []]
        epoques = [e for e in (_epoch(cp, d) for d in departs if d) if e is not None]
        if not epoques or dates["panier"] > min(epoques):
            fautes.append("panier.txt écrit après le démarrage de panier réparé")
    assert not fautes, message(
        en=f"The record of causes in ~/epreuve/constats is incomplete: {fautes}. Each cause is written "
        "from describe, the events or the logs BEFORE the repair, then left untouched.",
        fr=f"Le constat des causes dans ~/epreuve/constats est incomplet : {fautes}. Chaque cause s'écrit "
        "d'après describe, les événements ou les journaux AVANT la réparation, puis on n'y touche plus.",
    )


# ----------------------------------------------------------------------
# P16 : le champ modifié en direct porte la même valeur dans le manifeste
# versionné, lu par kubectl diff.
# ----------------------------------------------------------------------
def test_p16_la_modification_en_direct_est_dans_le_manifeste_versionne(cp):
    _api(cp)
    dep = _json(cp, f"-n {NS} get deployment panier") or {}
    montages = [m.get("mountPath") for c in ((dep.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or []
                for m in c.get("volumeMounts") or []]
    assert os.path.dirname(CONF_PANIER) in montages, message(
        en=f"In the cluster, panier mounts its configuration on {montages}: the repair made during the "
        f"incident ({os.path.dirname(CONF_PANIER)}) is not there.",
        fr=f"Dans le cluster, panier monte sa configuration sur {montages} : la réparation faite pendant "
        f"l'incident ({os.path.dirname(CONF_PANIER)}) n'y est pas.",
    )
    fichier = _depuis_le_depot(cp, "panier.yaml")
    assert fichier is not None, message(
        en="panier.yaml is missing from the last commit of ~/epreuve/manifestes.",
        fr="panier.yaml manque au dernier commit de ~/epreuve/manifestes.",
    )
    ecart = cp.run(f"{KUBECTL} diff -f {fichier}")
    assert ecart.rc == 0, message(
        en=f"kubectl diff between the last commit of panier.yaml and the cluster is not empty (code "
        f"{ecart.rc}): {ecart.stdout.strip()[-400:] or ecart.stderr.strip()[-200:]}. What was changed live "
        "is carried into the versioned manifest, otherwise the next apply undoes it.",
        fr=f"kubectl diff entre le dernier commit de panier.yaml et le cluster n'est pas vide (code "
        f"{ecart.rc}) : {ecart.stdout.strip()[-400:] or ecart.stderr.strip()[-200:]}. Ce qui a été changé "
        "en direct se reporte dans le manifeste versionné, sinon le prochain apply le défait.",
    )


# ----------------------------------------------------------------------
# P17 : aucun certificat du plan de contrôle n'expire avant trente jours.
# Repris de k8s-challenge-sauvegarder-et-restaurer (attesté).
# ----------------------------------------------------------------------
def test_p17_aucun_certificat_n_expire_avant_trente_jours(cp):
    res = cp.run("sudo kubeadm certs check-expiration -o json")
    assert res.rc == 0, message(
        en=f"kubeadm certs check-expiration failed: {res.stderr.strip()[:200]}",
        fr=f"kubeadm certs check-expiration échoue : {res.stderr.strip()[:200]}",
    )
    courts = {c["name"]: round(c.get("residualTime", 0) / 86400, 1)
              for c in json.loads(res.stdout).get("certificates", [])
              if c.get("residualTime", 0) < TRENTE_JOURS}
    assert not courts, message(
        en=f"These certificates expire in less than thirty days (days left): {courts}.",
        fr=f"Ces certificats expirent dans moins de trente jours (jours restants) : {courts}.",
    )


# ----------------------------------------------------------------------
# P18 : les réplicas de la vitrine sont sur des nœuds différents et portent
# une sonde de disponibilité.
# ----------------------------------------------------------------------
def test_p18_la_vitrine_est_repartie_et_porte_une_sonde_de_disponibilite(cp):
    _api(cp)
    dep = _vitrine(cp)
    gabarit = dep["spec"]["template"]["spec"]
    sondes = [c["name"] for c in gabarit.get("containers") or [] if c.get("readinessProbe")]
    assert sondes, message(
        en="No container of the storefront says when it is ready to receive traffic.",
        fr="Aucun conteneur de la vitrine ne dit quand il est prêt à recevoir du trafic.",
    )
    affinite = ((gabarit.get("affinity") or {}).get("podAntiAffinity") or {})
    termes = list(affinite.get("requiredDuringSchedulingIgnoredDuringExecution") or []) + [
        t.get("podAffinityTerm") or {} for t in affinite.get("preferredDuringSchedulingIgnoredDuringExecution") or []]
    regle = any(t.get("topologyKey") == HOSTNAME for t in termes) or any(
        t.get("topologyKey") == HOSTNAME for t in gabarit.get("topologySpreadConstraints") or [])
    assert regle, message(
        en="Nothing in the storefront's specification spreads its replicas over different nodes: two of "
        "them may land on the same node, and fall with it.",
        fr="Rien dans la spécification de la vitrine ne répartit ses réplicas sur des nœuds différents : "
        "deux d'entre eux peuvent tomber sur le même nœud, et tomber avec lui.",
    )
    voulues = dep["spec"].get("replicas", 1)
    prets: list[dict] = []
    for _ in range(18):
        prets = [p for p in _pods(cp, "app=vitrine") if _pret(p)]
        if len(prets) == voulues:
            break
        time.sleep(5)
    noeuds = [p["spec"].get("nodeName") for p in prets]
    assert voulues >= 2 and len(prets) == voulues and len(set(noeuds)) == len(noeuds), message(
        en=f"The storefront has {len(prets)} ready Pod(s) out of {voulues}, on {noeuds}: expected at least "
        "two, all ready, each on its own node.",
        fr=f"La vitrine a {len(prets)} Pod(s) prêt(s) sur {voulues}, sur {noeuds} : attendu au moins deux, "
        "tous prêts, chacun sur son nœud.",
    )
