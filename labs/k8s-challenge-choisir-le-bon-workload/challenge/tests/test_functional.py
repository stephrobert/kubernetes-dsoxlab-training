"""test_functional.py : k8s-challenge-choisir-le-bon-workload

Challenge du module « Workloads avancés ». Ces tests lisent l'état du cluster
« multi » (un control plane, deux workers). Un test vérifie un seul état
demandé par le cahier des charges.

Trois états sont bloquants (exam_blocking_checks) : la donnée du réplica 1 qui
survit à son Pod, le taint du control plane toujours présent et toléré par
l'agent, et la ressource Collecte conforme avec sa CRD Established.

Tous échouent avant le travail : entrepot est vide et la CRD n'est pas
installée. Une attente ne s'ouvre que si l'objet attendu existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/multi.kubeconfig"
NS = "entrepot"
BASE, REPLICAS, CHEMIN = "inventaire", 3, "/data"
MARQUE = f"{CHEMIN}/marque"
AGENT = "collecteur"
TAINT = "node-role.kubernetes.io/control-plane"
CRD, API = "collectes.atelier.formation.k8s", "atelier.formation.k8s/v1"
RESSOURCE = "journaux"
HORS_BORNES = re.compile(r"less than or equal to 90", re.IGNORECASE)
ATTENTE = 150
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-kind.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _instant(horodatage: str) -> float:
    return datetime.fromisoformat(horodatage.replace("Z", "+00:00")).timestamp()


def _attendre(host, args: str, pret) -> dict | None:
    objet = _json(host, args)
    fin = time.monotonic() + ATTENTE
    while objet is not None and not pret(objet) and time.monotonic() < fin:
        time.sleep(PAS)
        objet = _json(host, args) or objet
    return objet


def _sts_pret(sts: dict) -> bool:
    s = sts.get("status") or {}
    voulus = sts["spec"].get("replicas")
    return s.get("observedGeneration") == sts["metadata"]["generation"] \
        and s.get("readyReplicas") == voulus and s.get("updatedReplicas") == voulus


def _ds_pret(ds: dict) -> bool:
    s = ds.get("status") or {}
    return s.get("observedGeneration") == ds["metadata"]["generation"] \
        and s.get("desiredNumberScheduled", 0) > 0 and s.get("numberReady") == s.get("desiredNumberScheduled")


def _base(host) -> dict:
    sts = _attendre(host, f"-n {NS} get statefulset {BASE}", _sts_pret)
    if sts is None:
        pytest.fail(message(
            en=f"Nothing in {NS} serves {BASE} with replicas of stable identity.",
            fr=f"Rien dans {NS} ne sert {BASE} avec des réplicas à identité stable.",
        ))
    return sts


def _dans(host, pod: str, commande: str):
    return host.run(f"{ADMIN} -n {NS} exec {pod} -- {commande}")


def _noeuds(host) -> list[dict]:
    return (_json(host, "get nodes") or {}).get("items", [])


def _agent(host) -> dict:
    ds = _attendre(host, f"-n {NS} get daemonset {AGENT}", _ds_pret)
    if ds is None:
        pytest.fail(message(
            en=f"Nothing in {NS} runs the agent {AGENT} once per node.",
            fr=f"Rien dans {NS} ne fait tourner l'agent {AGENT} une fois par nœud.",
        ))
    return ds


# ----------------------------------------------------------------------
# 1. Trois réplicas ordonnés, tous Ready.
# ----------------------------------------------------------------------
def test_inventaire_a_trois_replicas_ordonnes_et_ready(host):
    sts = _base(host)
    prets = []
    for i in range(REPLICAS):
        p = _json(host, f"-n {NS} get pod {BASE}-{i}") or {}
        conditions = {c["type"]: c["status"] for c in (p.get("status") or {}).get("conditions") or []}
        if conditions.get("Ready") == "True":
            prets.append(f"{BASE}-{i}")
    assert sts["spec"].get("replicas") == REPLICAS and len(prets) == REPLICAS, message(
        en=f"{BASE} asks for {sts['spec'].get('replicas')} replica(s), Ready: {prets}. Expected {BASE}-0 to "
        f"{BASE}-2, all Ready.",
        fr=f"{BASE} demande {sts['spec'].get('replicas')} réplica(s), Ready : {prets}. Attendu {BASE}-0 à "
        f"{BASE}-2, tous Ready.",
    )


# ----------------------------------------------------------------------
# 2. Les noms stables se résolvent derrière un Service headless.
# ----------------------------------------------------------------------
def test_les_noms_stables_se_resolvent_derriere_un_service_headless(host):
    sts = _base(host)
    service = sts["spec"].get("serviceName") or ""
    svc = _json(host, f"-n {NS} get service {service}") if service else None
    ecarts = []
    for i in range(REPLICAS):
        ip = ((_json(host, f"-n {NS} get pod {BASE}-{i}") or {}).get("status") or {}).get("podIP")
        # La résolution de la libc, celle des applications, avec la liste search
        # du Pod. Le nslookup de busybox 1.38 l'ignore : le nom court y rend
        # NXDOMAIN alors qu'il se résout (mesuré le 2026-11-11, kind 1.37.0).
        res = _dans(host, f"{BASE}-{(i + 1) % REPLICAS}", f"ping -c 1 -W 2 {BASE}-{i}.{service}")
        premiere = res.stdout.splitlines()[0] if res.stdout else ""
        if not ip or f"({ip})" not in premiere:
            ecarts.append(f"{BASE}-{i}.{service}")
    assert svc is not None and svc["spec"].get("clusterIP") == "None" and not ecarts, message(
        en=f"The Service {service or '(none)'} of {BASE} is not headless, or these stable names do not resolve "
        f"to their Pod: {ecarts}.",
        fr=f"Le Service {service or '(aucun)'} de {BASE} n'est pas headless, ou ces noms stables ne se résolvent "
        f"pas vers leur Pod : {ecarts}.",
    )


# ----------------------------------------------------------------------
# 3. La donnée du réplica 1 survit à la suppression de son Pod. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_donnee_du_replica_1_survit_a_son_pod(host):
    _base(host)
    pod = _json(host, f"-n {NS} get pod {BASE}-1")
    assert pod is not None, message(en=f"No Pod {BASE}-1.", fr=f"Aucun Pod {BASE}-1.")
    res = _dans(host, f"{BASE}-1", f"head -n 1 {MARQUE}")
    contenu = res.stdout.strip() if res.rc == 0 else ""
    creations = [e for e in (_json(host, f"-n {NS} get events --field-selector reason=SuccessfulCreate") or {})
                 .get("items", []) if (e.get("involvedObject") or {}).get("kind") == "StatefulSet"
                 and f"Pod {BASE}-1 " in (e.get("message") or "")]
    fois = sum(e.get("count") or 1 for e in creations)
    ecrit = _dans(host, f"{BASE}-1", f"stat -c %Y {MARQUE}")
    intact = ecrit.rc == 0 and int(ecrit.stdout.strip()) < _instant(pod["metadata"]["creationTimestamp"])
    assert contenu == f"{BASE}-1" and fois >= 2 and intact, message(
        en=f"{MARQUE} on {BASE}-1 reads {contenu or 'nothing'!r}, its Pod was created {fois} time(s), and the "
        f"file {'predates' if intact else 'does not predate'} the current Pod. Expected the mark written on the "
        "volume of replica 1, read again intact by its recreated Pod.",
        fr=f"{MARQUE} sur {BASE}-1 vaut {contenu or 'rien'!r}, son Pod a été créé {fois} fois, et le fichier "
        f"{'précède' if intact else 'ne précède pas'} le Pod actuel. Attendu la marque écrite sur le volume du "
        "réplica 1, relue intacte par son Pod recréé.",
    )


# ----------------------------------------------------------------------
# 4. L'agent est prêt sur chaque nœud, control plane compris.
# ----------------------------------------------------------------------
def test_le_collecteur_est_pret_sur_chaque_noeud(host):
    ds = _agent(host)
    selecteur = ",".join(f"{k}={v}" for k, v in ds["spec"]["selector"].get("matchLabels", {}).items())
    prets = set()
    for p in (_json(host, f"-n {NS} get pods -l {selecteur}") or {}).get("items", []):
        conditions = {c["type"]: c["status"] for c in (p.get("status") or {}).get("conditions") or []}
        if conditions.get("Ready") == "True":
            prets.add(p["spec"].get("nodeName"))
    noeuds = {n["metadata"]["name"] for n in _noeuds(host)}
    assert noeuds and prets == noeuds, message(
        en=f"{AGENT} is Ready on {sorted(prets)}, the cluster has {sorted(noeuds)}. Expected one Ready agent on "
        "each node.",
        fr=f"{AGENT} est Ready sur {sorted(prets)}, le cluster compte {sorted(noeuds)}. Attendu un agent Ready "
        "sur chaque nœud.",
    )


# ----------------------------------------------------------------------
# 5. Le taint du control plane est présent, et l'agent le tolère. BLOQUANT.
# ----------------------------------------------------------------------
def test_le_taint_du_control_plane_est_present_et_tolere(host):
    plans = [n for n in _noeuds(host) if TAINT in (n["metadata"].get("labels") or {})]
    teintes = [t for n in plans for t in n["spec"].get("taints") or [] if t.get("key") == TAINT]
    assert plans and len(teintes) == len(plans), message(
        en="The taint of the control plane is gone: the agent must tolerate it, not remove it.",
        fr="Le taint du control plane a disparu : l'agent doit le tolérer, pas le retirer.",
    )
    ds = _json(host, f"-n {NS} get daemonset {AGENT}")
    tolerances = ((ds or {}).get("spec", {}).get("template", {}).get("spec") or {}).get("tolerations") or []

    def tolere(t: dict, taint: dict) -> bool:
        if t.get("effect") and t["effect"] != taint.get("effect"):
            return False
        if t.get("operator") == "Exists":
            return not t.get("key") or t["key"] == taint["key"]
        return t.get("key") == taint["key"] and t.get("value", "") == taint.get("value", "")

    assert ds is not None and all(any(tolere(t, taint) for t in tolerances) for taint in teintes), message(
        en=f"{AGENT} does not tolerate the taint of the control plane: it cannot run there.",
        fr=f"{AGENT} ne tolère pas le taint du control plane : il ne peut pas y tourner.",
    )


# ----------------------------------------------------------------------
# 6. La ressource Collecte est conforme, et sa CRD est Established. BLOQUANT.
# ----------------------------------------------------------------------
def test_la_collecte_journaux_est_conforme_et_sa_crd_established(host):
    crd = _json(host, f"get crd {CRD}")
    etablie = crd is not None and any(c.get("type") == "Established" and c.get("status") == "True"
                                      for c in (crd.get("status") or {}).get("conditions") or [])
    assert etablie, message(
        en=f"The CRD {CRD} is not installed, or not Established.",
        fr=f"La CRD {CRD} n'est pas installée, ou pas Established.",
    )
    r = _json(host, f"-n {NS} get {CRD} {RESSOURCE}")
    spec = (r or {}).get("spec") or {}
    assert spec == {"cible": "/var/log", "intervalleSecondes": 60, "retentionJours": 30}, message(
        en=f"The Collecte {RESSOURCE} has {spec or 'nothing'}. Expected the target, the interval and the "
        "retention of the requirements, and nothing else.",
        fr=f"La Collecte {RESSOURCE} porte {spec or 'rien'}. Attendu la cible, l'intervalle et la rétention du "
        "cahier des charges, et rien d'autre.",
    )


# ----------------------------------------------------------------------
# 7. Une rétention hors bornes est refusée par l'API.
# ----------------------------------------------------------------------
def test_une_retention_hors_bornes_est_refusee_en_dry_run_serveur(host):
    essai = (
        f"printf '%s' '{{\"apiVersion\":\"{API}\",\"kind\":\"Collecte\",\"metadata\":{{\"name\":\"essai-borne\","
        f"\"namespace\":\"{NS}\"}},\"spec\":{{\"cible\":\"/tmp\",\"intervalleSecondes\":60,"
        f"\"retentionJours\":120}}}}' | {ADMIN} apply --dry-run=server -f -"
    )
    res = host.run(essai)
    assert res.rc != 0 and HORS_BORNES.search(res.stderr), message(
        en="The API does not refuse a Collecte kept 120 days: the schema does not hold the requested bound.",
        fr="L'API ne refuse pas une Collecte gardée 120 jours : le schéma ne porte pas la borne demandée.",
    )
