"""test_functional.py : k8s-challenge-sauvegarder-et-restaurer

Challenge du module Administrer le cluster, sans procédure. Un test par état
demandé ; chacun échoue sur l'état de départ posé par le setup :

1. une sauvegarde fraîche d'etcd existe dans /var/backups/etcd/etcd-fraiche.db,
   lisible, et elle photographie l'état d'AVANT la restauration (révision au
   moins égale à celle du cluster à la fin du setup, donc plus récente que la
   sauvegarde de la veille) ;
2. etcd tourne sur un répertoire de données neuf, restauré, et le cluster est
   sain (API et deux nœuds Ready) ;
3. le namespace facturation et le ConfigMap tarifs sont revenus avec leurs UID
   d'origine : une restauration, pas une recréation ;
4. le ConfigMap intrus-apres-sauvegarde, écrit après la sauvegarde de la
   veille, n'existe plus ;
5. les manifestes de ~/depot n'emploient plus d'API retirée, et leurs objets
   existent dans le namespace depot avec leurs réglages ;
6. aucun certificat du plan de contrôle n'expire dans moins de trente jours,
   lu par kubeadm certs check-expiration.
"""

from __future__ import annotations

import json
import time

import pytest
import yaml

from conftest import lab_host, lab_target_host, message

ETAT = "/var/lib/dsoxlab/k8s-challenge-sauvegarder-et-restaurer.json"
FRAICHE = "/var/backups/etcd/etcd-fraiche.db"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"
API_RETIREES = {"autoscaling/v2beta2", "autoscaling/v2beta1", "policy/v1beta1", "extensions/v1beta1",
                "apps/v1beta1", "apps/v1beta2"}
TRENTE_JOURS = 30 * 24 * 3600


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def etat(host) -> dict:
    res = host.run(f"sudo cat {ETAT}")
    assert res.rc == 0, message(
        en=f"The state recorded by setup, {ETAT}, cannot be found: run dsoxlab run again.",
        fr=f"L'état noté par le setup, {ETAT}, est introuvable : rejouez dsoxlab run.",
    )
    return json.loads(res.stdout)


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _repertoire_d_etcd(host) -> tuple[str | None, str]:
    """Le hostPath monté sur le --data-dir de l'etcd EN MARCHE, demandé au runtime."""
    ids = host.run("sudo crictl ps --name '^etcd$' -q").stdout.split()
    if not ids:
        return None, "aucun conteneur etcd en marche"
    res = host.run(f"sudo crictl inspect {ids[0]}")
    if res.rc != 0:
        return None, res.stderr.strip()[:160]
    inspection = json.loads(res.stdout)
    config = (inspection.get("info") or {}).get("config") or {}
    arguments = list(config.get("args") or []) + list(config.get("command") or [])
    data_dir = next((a.split("=", 1)[1] for a in arguments if a.startswith("--data-dir=")), "/var/lib/etcd")
    montages = (inspection.get("status") or {}).get("mounts") or []
    source = next((m.get("hostPath") for m in montages if m.get("containerPath") == data_dir), None)
    return source, "" if source else f"aucun volume monté sur {data_dir}"


def _cluster_sain(host) -> tuple[bool, str]:
    res = _kubectl(host, "get --raw /readyz")
    if res.rc != 0 or res.stdout.strip() != "ok":
        return False, f"/readyz : {(res.stdout + res.stderr).strip()[:120]}"
    noeuds = json.loads(_kubectl(host, "get nodes -o json").stdout or "{}").get("items", [])
    pas_prets = [n["metadata"]["name"] for n in noeuds
                 if {c["type"]: c["status"] for c in n["status"].get("conditions", [])}.get("Ready") != "True"]
    if len(noeuds) < 2 or pas_prets:
        return False, f"{len(noeuds)} nœud(s), pas Ready : {pas_prets}"
    return True, ""


def test_une_sauvegarde_fraiche_photographie_l_etat_d_avant_la_restauration(host, etat):
    res = host.run(f"sudo etcdutl snapshot status {FRAICHE} -w json")
    assert res.rc == 0, message(
        en=f"No readable etcd snapshot at {FRAICHE}. You never restore without first backing up what "
        "you are about to overwrite.",
        fr=f"Aucun instantané etcd lisible dans {FRAICHE}. On ne restaure jamais sans avoir d'abord "
        "sauvegardé ce qu'on s'apprête à écraser.",
    )
    revision = json.loads(res.stdout).get("revision", 0)
    assert revision >= etat["revision"], message(
        en=f"The snapshot is at revision {revision}, the cluster was at {etat['revision']} when the "
        "challenge started: a copy of the previous day's backup does not photograph what was overwritten.",
        fr=f"L'instantané est à la révision {revision}, le cluster en était à {etat['revision']} au "
        "début du challenge : une copie de la sauvegarde de la veille ne photographie pas ce qui a été "
        "écrasé.",
    )
    # La révision ne suffit pas : après une restauration, l'API server écrit sans
    # cesse (baux, statuts), et la révision repasse vite au-dessus de celle du
    # setup (mesuré le 2026-11-13). La sauvegarde doit être PLUS ANCIENNE que le
    # répertoire restauré, quand il y en a un.
    source, _ = _repertoire_d_etcd(host)
    restaure = host.run(f"sudo stat -c %Y {source}/member") if source else None
    if restaure and restaure.rc == 0 and int(restaure.stdout.strip()) > int(etat["epoch"]):
        prise = int(host.check_output(f"sudo stat -c %Y {FRAICHE}").strip())
        assert prise <= int(restaure.stdout.strip()), message(
            en="The fresh backup was taken after the restore: it photographs the restored state, not the "
            "one that was overwritten.",
            fr="La sauvegarde fraîche a été prise après la restauration : elle photographie l'état "
            "restauré, pas celui qui a été écrasé.",
        )


def test_etcd_tourne_sur_un_repertoire_restaure_et_le_cluster_est_sain(host, etat):
    source, detail = _repertoire_d_etcd(host)
    assert source, message(en=f"etcd: {detail}.", fr=f"etcd : {detail}.")
    cree = host.run(f"sudo stat -c %Y {source}/member")
    assert cree.rc == 0 and int(cree.stdout.strip()) > int(etat["epoch"]), message(
        en=f"etcd runs on {source}, whose data predates the challenge: nothing was restored.",
        fr=f"etcd tourne sur {source}, dont les données datent d'avant le challenge : rien n'a été "
        "restauré.",
    )
    sain, detail = False, ""
    for _ in range(30):
        sain, detail = _cluster_sain(host)
        if sain:
            break
        time.sleep(4)
    assert sain, message(
        en=f"etcd was restored but the cluster is not healthy: {detail}.",
        fr=f"etcd a été restauré mais le cluster n'est pas sain : {detail}.",
    )


def test_les_objets_supprimes_sont_revenus_avec_leurs_uid(host, etat):
    ns = _kubectl(host, "get namespace facturation -o jsonpath='{.metadata.uid}'")
    cm = _kubectl(host, "-n facturation get configmap tarifs -o jsonpath='{.metadata.uid}'")
    trouves = {"facturation": ns.stdout.strip() if ns.rc == 0 else None,
               "tarifs": cm.stdout.strip() if cm.rc == 0 else None}
    attendus = {"facturation": etat["ns_uid"], "tarifs": etat["cm_uid"]}
    ecarts = {k: v for k, v in trouves.items() if v != attendus[k]}
    assert not ecarts, message(
        en=f"These objects are missing or do not carry their original UID: {ecarts}. A restore brings "
        "back the same objects; recreating them by hand gives new ones.",
        fr=f"Ces objets manquent ou ne portent pas leur UID d'origine : {ecarts}. Une restauration "
        "ramène les mêmes objets ; les recréer à la main en donne de nouveaux.",
    )


def test_l_objet_ecrit_apres_la_sauvegarde_n_existe_plus(host, etat):
    # Garde : sans restauration, on pourrait le supprimer à la main.
    source, _ = _repertoire_d_etcd(host)
    cree = host.run(f"sudo stat -c %Y {source}/member") if source else None
    restaure = bool(cree and cree.rc == 0 and int(cree.stdout.strip()) > int(etat["epoch"]))
    present = _kubectl(host, "-n default get configmap intrus-apres-sauvegarde").rc == 0
    etat_en = "still exists" if present else "is gone, but etcd was not restored"
    etat_fr = "existe encore" if present else "a disparu, mais etcd n'a pas été restauré"
    assert restaure and not present, message(
        en=f"intrus-apres-sauvegarde {etat_en}: written after the previous day's backup, it disappears "
        "with the restore of that backup.",
        fr=f"intrus-apres-sauvegarde {etat_fr} : écrit après la sauvegarde de la veille, il disparaît "
        "avec la restauration de cette sauvegarde.",
    )


def test_les_manifestes_du_depot_sont_migres_et_appliques(host):
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    fichiers = host.check_output(f"ls {maison}/depot/ 2>/dev/null || true").split()
    retirees = {}
    for nom in fichiers:
        for doc in yaml.safe_load_all(host.file(f"{maison}/depot/{nom}").content_string) or []:
            if doc and doc.get("apiVersion") in API_RETIREES:
                retirees[nom] = doc["apiVersion"]
    hpa = _kubectl(host, "-n depot get hpa catalogue -o json")
    pdb = _kubectl(host, "-n depot get pdb catalogue -o json")
    reglages = {}
    if hpa.rc == 0:
        h = json.loads(hpa.stdout)["spec"]
        reglages["hpa"] = (h.get("minReplicas"), h.get("maxReplicas"))
    if pdb.rc == 0:
        reglages["pdb"] = json.loads(pdb.stdout)["spec"].get("minAvailable")
    ok = not retirees and fichiers and reglages.get("hpa") == (2, 5) and reglages.get("pdb") == 1
    assert ok, message(
        en=f"The repository is not migrated: removed APIs still used {retirees or 'none'}, objects in the "
        f"cluster {reglages or 'none'} (expected HPA 2 to 5, PDB minAvailable 1).",
        fr=f"Le dépôt n'est pas migré : API retirées encore employées {retirees or 'aucune'}, objets dans "
        f"le cluster {reglages or 'aucun'} (attendu HPA de 2 à 5, PDB minAvailable 1).",
    )


def test_aucun_certificat_n_expire_avant_trente_jours(host):
    res = host.run("sudo kubeadm certs check-expiration -o json")
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
