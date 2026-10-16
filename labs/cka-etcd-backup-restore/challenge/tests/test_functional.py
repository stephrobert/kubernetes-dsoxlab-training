"""test_functional.py : cka-etcd-backup-restore

Ces tests lisent l'état du NŒUD et du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit la sauvegarde fraîche avec etcdutl et
exige qu'elle photographie l'état d'avant la restauration, par sa révision.
La deuxième lit, sur le nœud, la date de création du répertoire de données
que l'etcd en marche utilise : une restauration en crée un neuf, et un etcd
qui tourne encore sur un répertoire d'avant le lab n'a rien restauré, quoi
qu'on ait arrêté ou déplacé ; elle veut aussi le cluster sain après coup.
L'identité du membre ne sert pas de preuve : mesuré le 2026-09-15, etcd la
recalcule à partir des URL de pair et du jeton, et elle ne change pas. La
troisième compare les UID des objets revenus à ceux notés par le setup : un
namespace recréé à la main n'a pas le même. La quatrième cherche un objet
écrit après la sauvegarde d'hier soir, qui doit avoir disparu.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host, message

ETAT = "/var/lib/dsoxlab/cka-etcd-backup-restore.json"
SAUVEGARDE = "/opt/backup/etcd-snapshot.db"
PKI = "/etc/kubernetes/pki/etcd"
ETCDCTL = (
    f"etcdctl --endpoints=https://127.0.0.1:2379 --cacert={PKI}/ca.crt "
    f"--cert={PKI}/healthcheck-client.crt --key={PKI}/healthcheck-client.key"
)
NAMESPACE = "important-data"
CONFIGMAP = "mission-critical"
BRUIT = "bruit-apres-sauvegarde"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def etat(host) -> dict:
    res = host.run(f"sudo cat {ETAT}")
    assert res.rc == 0, message(
        en=f"The state recorded by setup, {ETAT}, cannot be found: run dsoxlab run again.",
        fr=f"L'état noté par le setup, {ETAT}, est introuvable : rejouer dsoxlab run.",
    )
    return json.loads(res.stdout)


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _api_saine(host) -> tuple[bool, str]:
    res = _kubectl(host, "get --raw /readyz")
    if res.rc != 0 or res.stdout.strip() != "ok":
        return False, f"/readyz : {(res.stdout + res.stderr).strip()[:160]}"
    res = _kubectl(host, "get nodes -o json")
    if res.rc != 0:
        return False, f"get nodes : {res.stderr.strip()[:160]}"
    noeuds = json.loads(res.stdout)["items"]
    pas_prets = [
        n["metadata"]["name"] for n in noeuds
        if {c["type"]: c["status"] for c in n["status"].get("conditions", [])}.get("Ready") != "True"
    ]
    if len(noeuds) < 2 or pas_prets:
        return False, f"{len(noeuds)} nœud(s), pas Ready : {pas_prets}"
    return True, ""


# ----------------------------------------------------------------------
# 1. La sauvegarde fraîche existe, est lisible, et date d'avant la restauration.
# ----------------------------------------------------------------------
def test_la_sauvegarde_fraiche_est_valide_et_anterieure(host, etat):
    res = host.run(f"sudo test -f {SAUVEGARDE}")
    assert res.rc == 0, message(
        en=f"No {SAUVEGARDE} file. The instruction starts there: you never restore "
        "without having backed up what you are about to overwrite.",
        fr=f"Aucun fichier {SAUVEGARDE}. La consigne commence par là : on ne restaure jamais "
        "sans avoir sauvegardé ce qu'on s'apprête à écraser.",
    )
    res = host.run(f"sudo etcdutl snapshot status {SAUVEGARDE} -w json")
    assert res.rc == 0, message(
        en=f"etcdutl cannot read {SAUVEGARDE}: {res.stderr.strip()[:200]}. This is not a "
        "valid etcd snapshot, or it was interrupted (a stray .part would say so).",
        fr=f"etcdutl ne lit pas {SAUVEGARDE} : {res.stderr.strip()[:200]}. Ce n'est pas un "
        "instantané etcd valide, ou il a été interrompu (un .part qui traîne le dirait).",
    )
    statut = json.loads(res.stdout)
    assert statut.get("totalKey", 0) > 0, message(
        en=f"The snapshot holds no key: {statut}.",
        fr=f"L'instantané ne contient aucune clé : {statut}.",
    )
    assert statut.get("revision", 0) >= etat["revision"], message(
        en=f"The snapshot is at revision {statut.get('revision')}, but the cluster was at "
        f"{etat['revision']} when the lab started. A backup taken after the restore, or a "
        "copy of last night's, does not photograph the state you overwrote.",
        fr=f"L'instantané est à la révision {statut.get('revision')}, mais le cluster en était à "
        f"{etat['revision']} au début du lab. Une sauvegarde prise après la restauration, ou une "
        "copie de celle d'hier soir, ne photographie pas l'état que vous avez écrasé.",
    )


# ----------------------------------------------------------------------
# 2. etcd tourne sur un répertoire restauré, et le cluster est sain.
# ----------------------------------------------------------------------
def test_etcd_a_ete_restaure_et_le_cluster_est_sain(host, etat):
    res = host.run(f"sudo {ETCDCTL} endpoint status -w json")
    assert res.rc == 0, message(
        en=f"etcd does not answer on 127.0.0.1:2379: {res.stderr.strip()[:200]}. Is the manifest "
        "back in /etc/kubernetes/manifests, and does it point at a directory that exists?",
        fr=f"etcd ne répond pas sur 127.0.0.1:2379 : {res.stderr.strip()[:200]}. Le manifeste "
        "est-il de retour dans /etc/kubernetes/manifests, et pointe-t-il un répertoire qui existe ?",
    )
    # Le répertoire que l'etcd EN MARCHE utilise, demandé au runtime : le Pod
    # miroir dans l'API peut être celui d'avant la restauration, mesuré le
    # 2026-09-15, puisque l'API vient d'être restaurée. crictl, lui, dit quel
    # hostPath est monté sur le --data-dir du conteneur.
    res = host.run("sudo crictl ps --name etcd -q")
    ids = res.stdout.split()
    assert ids, message(
        en="No etcd container running according to crictl, although port 2379 answers.",
        fr="Aucun conteneur etcd en marche d'après crictl, alors que le port 2379 répond.",
    )
    res = host.run(f"sudo crictl inspect {ids[0]}")
    assert res.rc == 0, message(
        en=f"crictl inspect failed: {res.stderr.strip()[:200]}",
        fr=f"crictl inspect échoue : {res.stderr.strip()[:200]}",
    )
    inspection = json.loads(res.stdout)
    config = (inspection.get("info") or {}).get("config") or {}
    arguments = list(config.get("args") or []) + list(config.get("command") or [])
    data_dir = next((a.split("=", 1)[1] for a in arguments if a.startswith("--data-dir=")), "/var/lib/etcd")
    montages = (inspection.get("status") or {}).get("mounts") or []
    source = next((m.get("hostPath") for m in montages if m.get("containerPath") == data_dir), None)
    assert source, message(
        en=f"The etcd container writes into {data_dir}, but no volume is mounted there (mounted: "
        f"{[(m.get('hostPath'), m.get('containerPath')) for m in montages]}). Changing --data-dir "
        "without changing the mount starts etcd empty inside the container: nothing survives.",
        fr=f"Le conteneur etcd écrit dans {data_dir}, mais aucun volume n'y est monté (montés : "
        f"{[(m.get('hostPath'), m.get('containerPath')) for m in montages]}). Changer --data-dir "
        "sans changer le montage fait démarrer etcd à vide dans le conteneur : rien ne survit.",
    )
    res = host.run(f"sudo stat -c %Y {source}/member")
    assert res.rc == 0, message(
        en=f"No member directory in {source}: etcd cannot run on this path. "
        "The manifest's hostPath must point at a directory etcdutl produced.",
        fr=f"Pas de répertoire member dans {source} : etcd ne peut pas tourner sur ce chemin. "
        "Le hostPath du manifeste doit pointer un répertoire que etcdutl a produit.",
    )
    cree_le = int(res.stdout.strip())
    assert cree_le > int(etat["epoch"]), message(
        en=f"etcd runs on {source}, whose data predates the lab. A restore "
        "produces a fresh directory; this one is still the original, so nothing was restored. "
        "Stopping the kubelet does not stop etcd: you have to move the manifest out, or point "
        "it at the restored directory.",
        fr=f"etcd tourne sur {source}, dont les données datent d'avant le lab. Une restauration "
        "produit un répertoire neuf : celui-ci est encore celui d'origine, rien n'a été restauré. "
        "Arrêter le kubelet n'arrête pas etcd ; c'est le manifeste qu'il faut sortir, ou faire "
        "pointer sur le répertoire restauré.",
    )
    saine, detail = False, ""
    for _ in range(30):
        saine, detail = _api_saine(host)
        if saine:
            break
        time.sleep(4)
    assert saine, message(
        en=f"etcd was restored but the cluster is not healthy after two minutes: {detail}. "
        "The API server and both nodes must be back.",
        fr=f"etcd a été restauré mais le cluster n'est pas sain après deux minutes : {detail}. "
        "L'API server et les deux nœuds doivent être revenus.",
    )


# ----------------------------------------------------------------------
# 3. Les données sont revenues telles qu'elles étaient.
# ----------------------------------------------------------------------
def test_les_donnees_sont_revenues_avec_leur_identite(host, etat):
    res = _kubectl(host, f"get namespace {NAMESPACE} -o json")
    assert res.rc == 0, message(
        en=f"Namespace {NAMESPACE} did not come back: {res.stderr.strip()[:200]}",
        fr=f"Le namespace {NAMESPACE} n'est pas revenu : {res.stderr.strip()[:200]}",
    )
    ns_uid = json.loads(res.stdout)["metadata"]["uid"]
    assert ns_uid == etat["ns_uid"], message(
        en=f"Namespace {NAMESPACE} exists, but with UID {ns_uid} instead of {etat['ns_uid']}: "
        "it was recreated, not restored. The data comes from the snapshot or it does not come back.",
        fr=f"Le namespace {NAMESPACE} existe, mais avec l'UID {ns_uid} au lieu de {etat['ns_uid']} : "
        "il a été recréé, pas restauré. Les données viennent de l'instantané ou ne reviennent pas.",
    )
    res = _kubectl(host, f"-n {NAMESPACE} get configmap {CONFIGMAP} -o json")
    assert res.rc == 0, message(
        en=f"ConfigMap {CONFIGMAP} did not come back in {NAMESPACE}.",
        fr=f"Le ConfigMap {CONFIGMAP} n'est pas revenu dans {NAMESPACE}.",
    )
    cm = json.loads(res.stdout)
    assert cm["metadata"]["uid"] == etat["cm_uid"], message(
        en=f"ConfigMap {CONFIGMAP} has UID {cm['metadata']['uid']} instead of {etat['cm_uid']}: recreated, not restored.",
        fr=f"Le ConfigMap {CONFIGMAP} a l'UID {cm['metadata']['uid']} au lieu de {etat['cm_uid']} : recréé, pas restauré.",
    )
    assert (cm.get("data") or {}).get("status") == "healthy", message(
        en=f"status is {(cm.get('data') or {}).get('status')!r}.",
        fr=f"status vaut {(cm.get('data') or {}).get('status')!r}.",
    )


# ----------------------------------------------------------------------
# 4. La preuve : ce qui a été écrit après la sauvegarde a disparu.
# ----------------------------------------------------------------------
def test_ce_qui_a_ete_ecrit_apres_la_sauvegarde_a_disparu(host):
    res = _kubectl(host, f"-n default get configmap {BRUIT} -o json")
    assert res.rc != 0, message(
        en=f"ConfigMap default/{BRUIT} still exists. It was written after last night's backup: "
        "if the cluster were running on the restored data, it would be gone. Either the restore "
        "never happened, or the API server is still serving its cache from before.",
        fr=f"Le ConfigMap default/{BRUIT} existe encore. Il a été écrit après la sauvegarde d'hier "
        "soir : si le cluster tournait sur les données restaurées, il n'existerait plus. Soit la "
        "restauration n'a pas eu lieu, soit l'API server sert encore son cache d'avant.",
    )
    res = _kubectl(host, "-n default get configmaps -o json")
    assert res.rc == 0, message(
        en=f"Listing the ConfigMaps of default failed: {res.stderr.strip()[:200]}",
        fr=f"La liste des ConfigMaps de default échoue : {res.stderr.strip()[:200]}",
    )
    noms = [c["metadata"]["name"] for c in json.loads(res.stdout)["items"]]
    assert BRUIT not in noms, message(
        en=f"{BRUIT} no longer exists on a direct read, but still appears in the list: the API "
        "server is serving a cache from before the restore. It must be restarted, by moving its "
        "manifest out and back.",
        fr=f"{BRUIT} n'existe plus en lecture directe, mais figure encore dans la liste : l'API "
        "server sert un cache d'avant la restauration. Il faut le relancer, en sortant puis "
        "remettant son manifeste.",
    )
