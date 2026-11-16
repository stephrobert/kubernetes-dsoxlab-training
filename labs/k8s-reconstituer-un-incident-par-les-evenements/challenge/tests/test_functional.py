"""test_functional.py : k8s-reconstituer-un-incident-par-les-evenements

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées. Cinq
applications tournent dans le namespace boutique ; quatre sont en panne, chacune
d'une façon que ses Events nomment par une raison différente, et une est saine.
Le setup tire au hasard quelle application porte quelle panne, et dans quel
ordre elles sont créées.

L'apprenant ne répare rien : il rédige le ConfigMap rapport. Aucune réponse
n'est écrite ici. La raison attendue se déduit de la spec du Deployment (la
panne y est posée), la première application touchée se lit dans les Events du
namespace au moment du check. Rien n'est vrai avant le travail : le rapport
n'existe pas.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "boutique"
KUBECTL = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
APPLICATIONS = ("panier", "paiement", "catalogue", "stock", "avis")
SAINE = "aucune"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, commande: str) -> dict:
    res = host.run(f"{KUBECTL} {commande} -o json")
    assert res.rc == 0, message(
        en=f"`kubectl {commande}` failed: {res.stderr.strip()}",
        fr=f"`kubectl {commande}` a échoué : {res.stderr.strip()}",
    )
    return json.loads(res.stdout)


def _rapport(host) -> dict[str, str]:
    res = host.run(f"{KUBECTL} -n {NAMESPACE} get configmap rapport -o json")
    assert res.rc == 0, message(
        en=f"No ConfigMap rapport in namespace {NAMESPACE}. Write the incident report there: one key per "
        "application, plus premiere-touchee.",
        fr=f"Aucun ConfigMap rapport dans le namespace {NAMESPACE}. Rédigez-y le rapport d'incident : une clé par "
        "application, plus premiere-touchee.",
    )
    return {k: v.strip() for k, v in (json.loads(res.stdout).get("data") or {}).items()}


def _panne(deploiement: dict) -> str:
    """La raison d'Event que la panne posée dans la spec produit."""
    spec = deploiement["spec"]["template"]["spec"]
    conteneur = spec["containers"][0]
    cpu = ((conteneur.get("resources") or {}).get("requests") or {}).get("cpu", "0")
    if cpu.isdigit() and int(cpu) >= 64:
        return "FailedScheduling"
    if any((v.get("configMap") or {}).get("name") == "config-absente" for v in spec.get("volumes") or []):
        return "FailedMount"
    if "readinessProbe" in conteneur:
        return "Unhealthy"
    if "exit 1" in " ".join(conteneur.get("command") or []):
        return "BackOff"
    return SAINE


def _pannes(host) -> dict[str, str]:
    deploiements = {d["metadata"]["name"]: d for d in _json(host, f"-n {NAMESPACE} get deployments")["items"]}
    manquants = [app for app in APPLICATIONS if app not in deploiements]
    assert not manquants, message(
        en=f"Deployments missing from {NAMESPACE}: {manquants}. The report describes the incident, nothing is to be "
        "deleted; `dsoxlab reset` sets the situation back.",
        fr=f"Deployments absents de {NAMESPACE} : {manquants}. Le rapport décrit l'incident, rien n'est à "
        "supprimer ; `dsoxlab reset` repose la situation.",
    )
    pannes = {app: _panne(deploiements[app]) for app in APPLICATIONS}
    assert sum(1 for p in pannes.values() if p != SAINE) == 4, message(
        en=f"Only {sum(1 for p in pannes.values() if p != SAINE)} faulty applications are left out of 4: something "
        "was repaired. The report describes the incident, it does not fix it; `dsoxlab reset` sets it back.",
        fr=f"Il ne reste que {sum(1 for p in pannes.values() if p != SAINE)} applications en panne sur 4 : quelque "
        "chose a été réparé. Le rapport décrit l'incident, il ne le corrige pas ; `dsoxlab reset` le repose.",
    )
    return pannes


# ----------------------------------------------------------------------
# 1. Chaque application porte la raison de ses Events Warning.
# ----------------------------------------------------------------------
def test_chaque_panne_est_nommee_par_sa_raison(host):
    pannes = _pannes(host)
    rapport = _rapport(host)
    fausses = {
        app: {"rapport": rapport.get(app), "events": attendu}
        for app, attendu in pannes.items()
        if attendu != SAINE and rapport.get(app) != attendu
    }
    assert not fausses, message(
        en=f"These applications do not carry the reason of their Warning Events: {fausses}. The value is the "
        "REASON column of `kubectl events -n boutique --types=Warning`, word for word.",
        fr=f"Ces applications ne portent pas la raison de leurs Events Warning : {fausses}. La valeur est la "
        "colonne REASON de `kubectl events -n boutique --types=Warning`, mot pour mot.",
    )


# ----------------------------------------------------------------------
# 2. L'application saine est dite saine.
# ----------------------------------------------------------------------
def test_l_application_saine_est_reconnue(host):
    pannes = _pannes(host)
    rapport = _rapport(host)
    saine = next(app for app, p in pannes.items() if p == SAINE)
    assert rapport.get(saine) == SAINE, message(
        en=f"The report gives {rapport.get(saine)!r} for {saine}, which has no Warning Event: write {SAINE!r} "
        "for it. A Normal Event is not an anomaly.",
        fr=f"Le rapport donne {rapport.get(saine)!r} pour {saine}, qui n'a aucun Event Warning : écrivez "
        f"{SAINE!r} pour elle. Un Event Normal n'est pas une anomalie.",
    )


# ----------------------------------------------------------------------
# 3. La chronologie : la première application touchée.
# ----------------------------------------------------------------------
def _horodatage(event: dict) -> str:
    return event.get("firstTimestamp") or event.get("eventTime") or event["metadata"]["creationTimestamp"]


def test_la_premiere_application_touchee_est_trouvee(host):
    rapport = _rapport(host)
    premiers: dict[str, str] = {}
    for event in _json(host, f"-n {NAMESPACE} get events --field-selector type=Warning")["items"]:
        nom = event["involvedObject"].get("name", "")
        app = next((a for a in APPLICATIONS if nom.startswith(f"{a}-")), None)
        if app:
            moment = _horodatage(event)
            premiers[app] = min(premiers.get(app, moment), moment)
    assert premiers, message(
        en="No Warning Event left in boutique: they live one hour (--event-ttl). Run `dsoxlab reset`, then "
        "rebuild the timeline within the hour.",
        fr="Plus aucun Event Warning dans boutique : ils vivent une heure (--event-ttl). Lancez `dsoxlab reset`, "
        "puis reconstituez la chronologie dans l'heure.",
    )
    premiere = min(premiers, key=lambda a: premiers[a])
    assert rapport.get("premiere-touchee") == premiere, message(
        en=f"The report names {rapport.get('premiere-touchee')!r} as the first application hit, but the first "
        f"Warning Event of the namespace concerns {premiere} (first Warning of each application: {premiers}).",
        fr=f"Le rapport nomme {rapport.get('premiere-touchee')!r} comme première application touchée, mais le "
        f"premier Event Warning du namespace concerne {premiere} (premier Warning de chaque application : "
        f"{premiers}).",
    )
