"""test_functional.py : cka-statefulset-identite-stable

Ces tests lisent l'état du cluster « lab » et l'intérieur des Pods, jamais les
commandes tapées. Un test vérifie un seul état.

Tous échouent avant le travail : identites ne contient que l'annuaire en
Deployment, sans StatefulSet, sans Service, sans revendication. Une attente ne
s'ouvre que si le StatefulSet existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time
from datetime import datetime

import pytest

from conftest import lab_host, lab_target_host, message

ADMIN = "sudo kubectl --kubeconfig /etc/kind/lab.kubeconfig"
NS = "identites"
NOM = "annuaire"
REPLICAS = 3
GABARIT, CHEMIN = "donnees", "/data"
FICHIER = f"{CHEMIN}/identite"
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


def _pret(sts: dict) -> bool:
    s = sts.get("status") or {}
    return s.get("observedGeneration") == sts["metadata"]["generation"] \
        and s.get("readyReplicas") == sts["spec"].get("replicas") \
        and s.get("updatedReplicas") == sts["spec"].get("replicas")


def _statefulset(host) -> dict | None:
    sts = _json(host, f"-n {NS} get statefulset {NOM}")
    fin = time.monotonic() + ATTENTE
    while sts is not None and not _pret(sts) and time.monotonic() < fin:
        time.sleep(PAS)
        sts = _json(host, f"-n {NS} get statefulset {NOM}") or sts
    return sts


def _sts_requis(host) -> dict:
    sts = _statefulset(host)
    if sts is None:
        pytest.fail(message(en=f"No StatefulSet {NOM} in {NS}.", fr=f"Aucun StatefulSet {NOM} dans {NS}."))
    return sts


def _pod(host, i: int) -> dict | None:
    return _json(host, f"-n {NS} get pod {NOM}-{i}")


def _dans(host, pod: str, commande: str):
    return host.run(f"{ADMIN} -n {NS} exec {pod} -- {commande}")


# ----------------------------------------------------------------------
# 1. Un StatefulSet à trois réplicas, ordonnés de 0 à 2, tous Ready.
# ----------------------------------------------------------------------
def test_le_statefulset_annuaire_a_trois_replicas_ready(host):
    sts = _sts_requis(host)
    prets = []
    for i in range(REPLICAS):
        p = _pod(host, i)
        conditions = {c["type"]: c["status"] for c in ((p or {}).get("status") or {}).get("conditions") or []}
        proprietaire = [o.get("kind") for o in ((p or {}).get("metadata") or {}).get("ownerReferences") or []]
        if conditions.get("Ready") == "True" and "StatefulSet" in proprietaire:
            prets.append(f"{NOM}-{i}")
    assert sts["spec"].get("replicas") == REPLICAS and len(prets) == REPLICAS, message(
        en=f"{NOM} asks for {sts['spec'].get('replicas')} replica(s), Ready Pods: {prets}. Expected {NOM}-0, "
        f"{NOM}-1 and {NOM}-2, all Ready.",
        fr=f"{NOM} demande {sts['spec'].get('replicas')} réplica(s), Pods Ready : {prets}. Attendu {NOM}-0, "
        f"{NOM}-1 et {NOM}-2, tous Ready.",
    )


# ----------------------------------------------------------------------
# 2. Un Service headless porte le StatefulSet.
# ----------------------------------------------------------------------
def test_le_service_annuaire_est_headless_et_gouverne_le_statefulset(host):
    sts = _sts_requis(host)
    svc = _json(host, f"-n {NS} get service {NOM}")
    assert svc is not None, message(en=f"No Service {NOM} in {NS}.", fr=f"Aucun Service {NOM} dans {NS}.")
    etiquettes = sts["spec"]["template"]["metadata"].get("labels") or {}
    selecteur = svc["spec"].get("selector") or {}
    assert svc["spec"].get("clusterIP") == "None" and sts["spec"].get("serviceName") == NOM \
        and selecteur and all(etiquettes.get(k) == v for k, v in selecteur.items()), message(
        en=f"Service {NOM}: clusterIP {svc['spec'].get('clusterIP')!r}, selector {selecteur}; the StatefulSet "
        f"names the Service {sts['spec'].get('serviceName')!r}. Expected a headless Service that selects the "
        "Pods of the StatefulSet, and that the StatefulSet names.",
        fr=f"Service {NOM} : clusterIP {svc['spec'].get('clusterIP')!r}, sélecteur {selecteur} ; le StatefulSet "
        f"désigne le Service {sts['spec'].get('serviceName')!r}. Attendu un Service headless qui sélectionne les "
        "Pods du StatefulSet, et que le StatefulSet désigne.",
    )


# ----------------------------------------------------------------------
# 3. Chaque Pod se résout par son nom stable, depuis un autre Pod.
# ----------------------------------------------------------------------
def test_chaque_pod_se_resout_par_son_nom_stable(host):
    _sts_requis(host)
    ecarts = []
    for i in range(REPLICAS):
        cible, client = _pod(host, i), f"{NOM}-{(i + 1) % REPLICAS}"
        ip = ((cible or {}).get("status") or {}).get("podIP")
        # La résolution de la libc, celle des applications, avec la liste search
        # du Pod. Le nslookup de busybox 1.38 l'ignore : le nom court y rend
        # NXDOMAIN alors qu'il se résout (mesuré le 2026-11-11, kind 1.37.0).
        res = _dans(host, client, f"ping -c 1 -W 2 {NOM}-{i}.{NOM}")
        premiere = res.stdout.splitlines()[0] if res.stdout else ""
        if not ip or f"({ip})" not in premiere:
            ecarts.append(f"{NOM}-{i}.{NOM}")
    assert not ecarts, message(
        en=f"From another Pod, these stable names do not resolve to their Pod: {ecarts}.",
        fr=f"Depuis un autre Pod, ces noms stables ne se résolvent pas vers leur Pod : {ecarts}.",
    )


# ----------------------------------------------------------------------
# 4. Chaque réplica a sa propre revendication, montée sur /data.
# ----------------------------------------------------------------------
def test_chaque_replica_a_sa_propre_revendication(host):
    sts = _sts_requis(host)
    gabarits = [g["metadata"]["name"] for g in sts["spec"].get("volumeClaimTemplates") or []]
    montes = [m.get("name") for c in sts["spec"]["template"]["spec"]["containers"]
              for m in c.get("volumeMounts") or [] if m.get("mountPath") == CHEMIN]
    liees = [f"{GABARIT}-{NOM}-{i}" for i in range(REPLICAS)
             if ((_json(host, f"-n {NS} get pvc {GABARIT}-{NOM}-{i}") or {}).get("status") or {}).get("phase")
             == "Bound"]
    assert GABARIT in gabarits and GABARIT in montes and len(liees) == REPLICAS, message(
        en=f"Claim templates: {gabarits}, mounted on {CHEMIN}: {montes}, Bound claims: {liees}. Expected a "
        f"template named {GABARIT}, mounted on {CHEMIN}, and one Bound claim per replica.",
        fr=f"Gabarits de revendication : {gabarits}, montés sur {CHEMIN} : {montes}, revendications Bound : "
        f"{liees}. Attendu un gabarit nommé {GABARIT}, monté sur {CHEMIN}, et une revendication Bound par réplica.",
    )


# ----------------------------------------------------------------------
# 5. La donnée du réplica 1 survit à la suppression de son Pod.
# ----------------------------------------------------------------------
def test_la_donnee_du_replica_1_survit_a_son_pod(host):
    _sts_requis(host)
    pod = _pod(host, 1)
    assert pod is not None, message(en=f"No Pod {NOM}-1.", fr=f"Aucun Pod {NOM}-1.")
    res = _dans(host, f"{NOM}-1", f"head -n 1 {FICHIER}")
    contenu = res.stdout.strip() if res.rc == 0 else ""
    creations = [e for e in (_json(host, f"-n {NS} get events --field-selector reason=SuccessfulCreate") or {})
                 .get("items", []) if (e.get("involvedObject") or {}).get("kind") == "StatefulSet"
                 and f"Pod {NOM}-1 " in (e.get("message") or "")]
    fois = sum(e.get("count") or 1 for e in creations) if creations else 0
    assert contenu == f"{NOM}-1" and fois >= 2, message(
        en=f"{FICHIER} on {NOM}-1 reads {contenu or 'nothing'!r}, and its Pod was created {fois} time(s). "
        f"Expected the name {NOM}-1 written in the volume, read again by a Pod created again since.",
        fr=f"{FICHIER} sur {NOM}-1 vaut {contenu or 'rien'!r}, et son Pod a été créé {fois} fois. Attendu le nom "
        f"{NOM}-1 écrit dans le volume, relu par un Pod recréé depuis.",
    )
    ecrit = _dans(host, f"{NOM}-1", f"stat -c %Y {FICHIER}")
    assert ecrit.rc == 0 and int(ecrit.stdout.strip()) < _instant(pod["metadata"]["creationTimestamp"]), message(
        en=f"{FICHIER} was written after the current Pod was created: nothing shows that it survived.",
        fr=f"{FICHIER} a été écrit après la création du Pod actuel : rien ne montre qu'il a survécu.",
    )


# ----------------------------------------------------------------------
# 6. Le Deployment a laissé la place.
# ----------------------------------------------------------------------
def test_le_deployment_annuaire_a_laisse_la_place(host):
    _sts_requis(host)
    assert _json(host, f"-n {NS} get deployment {NOM}") is None, message(
        en=f"The Deployment {NOM} still runs next to the StatefulSet: two annuaires answer.",
        fr=f"Le Deployment {NOM} tourne encore à côté du StatefulSet : deux annuaires répondent.",
    )
