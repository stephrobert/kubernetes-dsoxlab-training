"""test_functional.py : k8s-auditer-les-flux-avec-hubble

Lab guidé de la leçon L4 du niveau 6 « Réseau avancé » (CKNE), sur le cluster
Cilium sans kube-proxy des hôtes net-*. Le setup pose dans le namespace
magasin une API sur net-w1.lab, trois clients sur net-w2.lab qui l'appellent
toutes les deux secondes, et une NetworkPolicy qui refuse l'un d'eux, tiré au
sort. Seul root lit son nom, dans /var/lib/dsoxlab-labs/.

Chaque test lit un état du cluster ou d'un nœud, dans l'ordre de la fiche :

1. le constat est consigné dans le ConfigMap `constat` du namespace magasin :
   `pod-source` nomme le client refusé, `raison` la raison du refus telle que
   Hubble la donne. La raison attendue n'est pas écrite ici : elle est relue
   dans Hubble lui-même, sur l'agent de net-w1.lab ;
2. la métrique qui compte ce refus le désigne : sur le port 9965 de
   net-w1.lab, `hubble_drop_total` porte une série dont la source est
   magasin/<client refusé>, et elle augmente encore (la politique refuse
   toujours, rien n'a été « réparé ») ;
3. les refus sont journalisés sur le nœud : l'export Hubble de net-w1.lab écrit
   dans /var/run/cilium/hubble/events.log des flux DROPPED du client refusé, et
   rien d'autre que des flux DROPPED.

Les trois échouent sur l'état de départ : aucun ConfigMap constat, la métrique
drop du socle ne porte ni source ni destination, et le socle n'exporte aucun
flux.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_host_ip, message

ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
PLAN = "net-cp.lab"
NOEUD_API = "net-w1.lab"
NS = "magasin"
REFERENCE = "/var/lib/dsoxlab-labs/k8s-auditer-les-flux-avec-hubble.ref"
JOURNAL = "/var/run/cilium/hubble/events.log"
METRIQUES = 9965


@pytest.fixture(scope="module")
def cp():
    return lab_host(PLAN)


@pytest.fixture(scope="module")
def refuse(cp) -> str:
    return cp.run(f"sudo cat {REFERENCE}").stdout.strip()


def _json(cp, args: str) -> dict | None:
    res = cp.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _agent_du_noeud(cp, noeud: str) -> str | None:
    pods = (_json(cp, "-n kube-system get pods -l k8s-app=cilium") or {}).get("items", [])
    return next((p["metadata"]["name"] for p in pods
                 if p["spec"].get("nodeName") == noeud and p.get("status", {}).get("phase") == "Running"), None)


def _flux(lignes: str) -> list[dict]:
    """Les flux d'une sortie JSON de Hubble, une ligne par événement."""
    flux = []
    for ligne in lignes.splitlines():
        try:
            evenement = json.loads(ligne)
        except ValueError:
            continue
        if isinstance(evenement, dict) and isinstance(evenement.get("flow"), dict):
            flux.append(evenement["flow"])
    return flux


def _normaliser(raison: str) -> str:
    return re.sub(r"[\s-]+", "_", raison.strip()).upper()


def _raisons_observees(cp, refuse: str) -> set[str]:
    """Les raisons de refus que Hubble donne, sur net-w1.lab, pour le client refusé."""
    agent = _agent_du_noeud(cp, NOEUD_API)
    if not agent or not refuse:
        return set()
    sortie = cp.run(
        f"{ADMIN} -n kube-system exec {agent} -c cilium-agent -- "
        f"hubble observe --namespace {NS} --verdict DROPPED --last 200 -o json").stdout
    return {
        f.get("drop_reason_desc", "") for f in _flux(sortie)
        if (f.get("source") or {}).get("pod_name") == refuse and f.get("drop_reason_desc")
    }


def test_le_constat_designe_le_flux_refuse(cp, refuse):
    donnees = (_json(cp, f"-n {NS} get configmap constat") or {}).get("data") or {}
    source = donnees.get("pod-source", "").strip()
    raison = _normaliser(donnees.get("raison", ""))
    observees = {_normaliser(r) for r in _raisons_observees(cp, refuse)}
    assert donnees and source == refuse and raison in observees, message(
        en=(f"No ConfigMap constat in namespace {NS}, with the keys pod-source and raison."
            if not donnees else
            f"The constat names pod-source={source!r} and raison={donnees.get('raison', '')!r}. That is not "
            f"the refused flow Hubble shows on {NOEUD_API}: hubble observe --namespace {NS} --verdict DROPPED, "
            "in the Cilium agent of that node, names the source Pod and the drop reason."),
        fr=(f"Aucun ConfigMap constat dans le namespace {NS}, avec les clés pod-source et raison."
            if not donnees else
            f"Le constat nomme pod-source={source!r} et raison={donnees.get('raison', '')!r}. Ce n'est pas le "
            f"flux refusé que montre Hubble sur {NOEUD_API} : hubble observe --namespace {NS} --verdict "
            "DROPPED, dans l'agent Cilium de ce nœud, nomme le Pod source et la raison du refus."),
    )


def _compte_des_refus(cp, refuse: str) -> float | None:
    """La somme des séries hubble_drop_total dont la source est le client refusé."""
    ip = lab_host_ip(NOEUD_API)
    sortie = cp.run(f"curl -s --max-time 5 http://{ip}:{METRIQUES}/metrics").stdout
    source = f'source="{NS}/{refuse}"'
    valeurs = [
        float(ligne.rsplit(" ", 1)[1]) for ligne in sortie.splitlines()
        if ligne.startswith("hubble_drop_total{") and source in ligne
    ]
    return sum(valeurs) if valeurs else None


def test_la_metrique_compte_les_refus_du_client(cp, refuse):
    avant = _compte_des_refus(cp, refuse) if refuse else None
    time.sleep(12)
    apres = _compte_des_refus(cp, refuse) if refuse else None
    assert avant is not None and apres is not None and apres > avant, message(
        en=(f"No hubble_drop_total series with the source {NS}/{refuse} on {NOEUD_API}:{METRIQUES}. The drop "
            "metric only carries the reason and the protocol until it is given a source and destination "
            "context (drop:sourceContext=pod;destinationContext=pod)."
            if avant is None or apres is None else
            f"The hubble_drop_total series of {NS}/{refuse} no longer grows ({avant} then {apres} twelve "
            "seconds later): the flow is no longer refused. The lab audits the refusal, it does not remove it."),
        fr=(f"Aucune série hubble_drop_total de source {NS}/{refuse} sur {NOEUD_API}:{METRIQUES}. La métrique "
            "drop ne porte que la raison et le protocole tant qu'on ne lui donne pas un contexte de source et "
            "de destination (drop:sourceContext=pod;destinationContext=pod)."
            if avant is None or apres is None else
            f"La série hubble_drop_total de {NS}/{refuse} n'augmente plus ({avant} puis {apres} douze secondes "
            "plus tard) : le flux n'est plus refusé. Le lab audite le refus, il ne le retire pas."),
    )


def test_les_refus_sont_journalises_sur_le_noeud(refuse):
    noeud = lab_host(NOEUD_API)
    fichier = noeud.file(JOURNAL)
    flux = _flux(noeud.run(f"sudo tail -n 2000 {JOURNAL}").stdout) if fichier.exists else []
    du_client = [f for f in flux if (f.get("source") or {}).get("pod_name") == refuse
                 and f.get("verdict") == "DROPPED"]
    autres = sorted({f.get("verdict", "?") for f in flux if f.get("verdict") != "DROPPED"})
    assert du_client and not autres, message(
        en=(f"{JOURNAL} is missing on {NOEUD_API}: Hubble exports no flow to a file."
            if not fichier.exists else
            f"{JOURNAL} on {NOEUD_API} holds {len(flux)} flow(s), {len(du_client)} of them DROPPED from "
            f"{refuse}, and other verdicts {autres or 'none'}. Expected: the refusals of {refuse}, and only "
            "DROPPED flows (an allowList on the verdict)."),
        fr=(f"{JOURNAL} est absent de {NOEUD_API} : Hubble n'exporte aucun flux dans un fichier."
            if not fichier.exists else
            f"{JOURNAL} sur {NOEUD_API} porte {len(flux)} flux, dont {len(du_client)} DROPPED venant de "
            f"{refuse}, et d'autres verdicts {autres or 'aucun'}. Attendu : les refus de {refuse}, et "
            "seulement des flux DROPPED (une allowList sur le verdict)."),
    )
