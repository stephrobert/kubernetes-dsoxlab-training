"""test_functional.py : k8s-challenge-retrouver-les-flux-refuses

Challenge de la compétence « Retrouver, compter et journaliser les flux
refusés avec Hubble », sur le cluster Cilium sans kube-proxy des hôtes net-*.

La préparation tire au sort, dans le namespace livraison, le client refusé,
la destination qu'il ne peut plus joindre, donc aussi le nœud où se produit
le refus : une NetworkPolicy de SORTIE l'applique au départ, sur l'agent
Cilium du nœud du client. Un second refus, dans le namespace voisin, tourne
sur le même nœud. Seul root lit la référence.

Deux tests sont bloquants, parce qu'ils portent le cœur du geste : le flux
refusé désigné tel que Hubble le montre, et la métrique qui le compte avec
sa source et sa destination.

Les trois tests échouent sur l'état de départ : aucun
ConfigMap refus, la métrique drop du socle ne porte ni source ni
destination, et le socle n'exporte aucun flux. Le test de la métrique
exige aussi que le refus soit resté en place et que le flux permis passe
toujours : le refus s'audite, il ne se lève pas.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_host_ip, message

ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
PLAN = "net-cp.lab"
NS, VOISIN = "livraison", "voisin"
REFERENCE = "/var/lib/dsoxlab-labs/k8s-challenge-retrouver-les-flux-refuses.json"
JOURNAL = "/var/run/cilium/hubble/refus-livraison.log"
METRIQUES = 9965


@pytest.fixture(scope="module")
def cp():
    return lab_host(PLAN)


@pytest.fixture(scope="module")
def reference(cp) -> dict:
    res = cp.run(f"sudo cat {REFERENCE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The reference of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La référence de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


def _json(cp, args: str) -> dict | None:
    res = cp.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _flux(lignes: str) -> list[dict]:
    flux = []
    for ligne in lignes.splitlines():
        try:
            evenement = json.loads(ligne)
        except ValueError:
            continue
        if isinstance(evenement, dict) and isinstance(evenement.get("flow"), dict):
            flux.append(evenement["flow"])
    return flux


# ----------------------------------------------------------------------
# 1. Le flux refusé est désigné tel que Hubble le montre. BLOQUANT.
# ----------------------------------------------------------------------
def test_le_flux_refuse_est_designe(cp, reference):
    donnees = (_json(cp, f"-n {NS} get configmap refus") or {}).get("data") or {}
    lu = {cle: donnees.get(cle, "").strip().split("/")[-1] for cle in ("source", "destination", "noeud")}
    attendu = {cle: reference[cle] for cle in ("source", "destination", "noeud")}
    assert lu == attendu, message(
        en=(f"No ConfigMap refus in namespace {NS}, with the keys source, destination and noeud."
            if not donnees else
            f"The ConfigMap refus names source={lu['source'] or '?'}, destination={lu['destination'] or '?'}, "
            f"noeud={lu['noeud'] or '?'}: it is not the flow the policy refuses. The refusal of an egress "
            "policy is seen by the Cilium agent of the node where the client runs."),
        fr=(f"Aucun ConfigMap refus dans le namespace {NS}, avec les clés source, destination et noeud."
            if not donnees else
            f"Le ConfigMap refus nomme source={lu['source'] or '?'}, destination={lu['destination'] or '?'}, "
            f"noeud={lu['noeud'] or '?'} : ce n'est pas le flux que la politique refuse. Le refus d'une "
            "politique de sortie se voit sur l'agent Cilium du nœud où tourne le client."),
    )


# ----------------------------------------------------------------------
# 2. La métrique compte ce refus, avec sa source et sa destination. BLOQUANT.
# ----------------------------------------------------------------------
def _compte(cp, reference: dict) -> float | None:
    ip = lab_host_ip(reference["noeud"])
    sortie = cp.run(f"curl -s --max-time 5 http://{ip}:{METRIQUES}/metrics").stdout
    source = f'source="{NS}/{reference["source"]}"'
    destination = f'destination="{NS}/{reference["destination"]}"'
    valeurs = [
        float(ligne.rsplit(" ", 1)[1]) for ligne in sortie.splitlines()
        if ligne.startswith("hubble_drop_total{") and source in ligne and destination in ligne
    ]
    return sum(valeurs) if valeurs else None


def test_la_metrique_compte_le_refus_avec_source_et_destination(cp, reference):
    avant = _compte(cp, reference)
    time.sleep(12)
    apres = _compte(cp, reference)
    assert avant is not None and apres is not None and apres > avant, message(
        en=(f"No hubble_drop_total series on the metrics port {METRIQUES} of the node of the refusal that "
            "names both the source Pod and the destination Pod of the refused flow."
            if avant is None or apres is None else
            f"The series of the refused flow no longer grows ({avant} then {apres} twelve seconds later): the "
            "flow is no longer refused. The refusal is audited, not lifted."),
        fr=(f"Aucune série hubble_drop_total, sur le port de métriques {METRIQUES} du nœud du refus, qui nomme "
            "à la fois le Pod source et le Pod destination du flux refusé."
            if avant is None or apres is None else
            f"La série du flux refusé n'augmente plus ({avant} puis {apres} douze secondes plus tard) : le flux "
            "n'est plus refusé. Le refus s'audite, il ne se lève pas."),
    )
    _refus_intact(cp, reference)


# ----------------------------------------------------------------------
# 3. Les refus de livraison, et eux seuls, sont journalisés sur le nœud.
# ----------------------------------------------------------------------
def test_les_refus_de_livraison_et_eux_seuls_sont_journalises(reference):
    noeud = lab_host(reference["noeud"])
    present = noeud.file(JOURNAL).exists
    flux = _flux(noeud.run(f"sudo tail -n 3000 {JOURNAL}").stdout) if present else []
    du_client = [f for f in flux if (f.get("source") or {}).get("pod_name") == reference["source"]
                 and f.get("verdict") == "DROPPED"]
    hors_sujet = [f for f in flux
                  if f.get("verdict") != "DROPPED"
                  or NS not in {(f.get("source") or {}).get("namespace"), (f.get("destination") or {}).get("namespace")}]
    assert du_client and not hors_sujet, message(
        en=(f"{JOURNAL} is missing on the node of the refusal: Hubble exports no flow to that file."
            if not present else
            f"{JOURNAL} holds {len(flux)} flow(s), {len(du_client)} of them DROPPED from the refused client, and "
            f"{len(hors_sujet)} that are not a refusal of namespace {NS}. Expected the refusals of {NS}, and "
            "nothing else: neither other verdicts, nor the refusals of other namespaces."),
        fr=(f"{JOURNAL} est absent du nœud du refus : Hubble n'exporte aucun flux dans ce fichier."
            if not present else
            f"{JOURNAL} porte {len(flux)} flux, dont {len(du_client)} DROPPED venant du client refusé, et "
            f"{len(hors_sujet)} qui ne sont pas un refus du namespace {NS}. Attendu les refus de {NS}, et rien "
            "d'autre : ni d'autres verdicts, ni les refus d'autres namespaces."),
    )


def _refus_intact(cp, reference: dict) -> None:
    """Le refus reste en place, et le flux permis passe toujours."""
    politique = _json(cp, f"-n {NS} get networkpolicy profil-restreint")
    permis = cp.run(f"{ADMIN} -n {NS} exec {reference['source']} -- "
                    f"wget -q -T 3 -O /dev/null http://{reference['permise']}").rc == 0
    refuse = cp.run(f"{ADMIN} -n {NS} exec {reference['source']} -- "
                    f"wget -q -T 3 -O /dev/null http://{reference['destination']}").rc == 0
    assert politique is not None and permis and not refuse, message(
        en=f"The policy profil-restreint {'is in place' if politique else 'is gone'}, the refused client "
        f"{'still reaches' if permis else 'no longer reaches'} its allowed destination and "
        f"{'now reaches' if refuse else 'still cannot reach'} the refused one. Expected the refusal untouched.",
        fr=f"La politique profil-restreint {'est en place' if politique else 'a disparu'}, le client refusé "
        f"{'joint toujours' if permis else 'ne joint plus'} sa destination permise et "
        f"{'joint désormais' if refuse else 'ne joint toujours pas'} celle qui lui est refusée. Attendu : le "
        "refus intact.",
    )
