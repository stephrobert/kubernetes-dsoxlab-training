"""test_functional.py : k8s-mesurer-un-slo-et-ecrire-un-runbook

Ces tests lisent l'état du cluster et JOUENT le runbook, jamais les commandes
tapées.

Un runbook se juge à ce qu'il fait quand quelqu'un d'autre le rejoue. Les
tests recassent donc l'application de la même façon que l'incident d'origine,
lancent le runbook, et vérifient que le service est revenu. Puis ils le
rejouent sur un service sain : il doit sortir en 0 sans rien changer. Un
runbook qui annule une révision sans regarder l'état d'abord casserait un
service qui marche, et c'est l'erreur que ce second passage attrape.

Le nombre de minutes en panne du journal de la sonde est tiré au sort à la
préparation, et gardé dans une mémoire lisible par root seulement : le SLI et
le budget à trouver changent à chaque passage.

Tous échouent avant le travail : le service est en panne, le runbook n'existe
pas, et le ConfigMap slo-catalogue non plus.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

NS = "catalogue"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NG = "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
MAUVAISE = "nginx:1.30.5-introuvable"
MEMOIRE = "/var/lib/dsoxlab/k8s-mesurer-un-slo-et-ecrire-un-runbook.json"
SLO = 99.5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def runbook(host) -> str:
    maison = host.check_output('getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6').strip()
    return f"{maison}/runbooks/catalogue-indisponible.sh"


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


def _json(host, args: str) -> dict:
    res = host.run(f"{ADMIN} {args} -o json")
    return json.loads(res.stdout) if res.rc == 0 and res.stdout.strip() else {}


def _etat(host) -> tuple[int, str, str]:
    """(réplicas disponibles, image, révision) du Deployment catalogue."""
    d = _json(host, f"-n {NS} get deployment catalogue")
    disponibles = (d.get("status") or {}).get("availableReplicas", 0)
    conteneurs = ((d.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or [{}]
    revision = ((d.get("metadata") or {}).get("annotations") or {}).get("deployment.kubernetes.io/revision", "")
    return disponibles, conteneurs[0].get("image", ""), revision


def _repond(host) -> bool:
    ip = host.run(ADMIN + " -n " + NS + " get service catalogue -o jsonpath='{.spec.clusterIP}'").stdout.strip()
    code = host.run("curl -s -m 5 -o /dev/null -w '%{http_code}' http://" + ip + "/").stdout if ip else ""
    return code == "200"


def _jouer(host, runbook: str):
    return host.run(f"timeout 300 bash {runbook} < /dev/null")


def _consigne(host) -> dict:
    return (_json(host, f"-n {NS} get configmap slo-catalogue") or {}).get("data") or {}


# ----------------------------------------------------------------------
# 1. Le service répond, sur sa dernière bonne image.
# ----------------------------------------------------------------------
def test_le_catalogue_repond_sur_sa_bonne_image(host):
    host.run(f"{ADMIN} -n {NS} rollout status deployment/catalogue --timeout=60s")
    disponibles, image, _ = _etat(host)
    assert disponibles >= 2 and image == NG and _repond(host), message(
        en=f"catalogue has {disponibles} available replica(s), on image {image or '?'}, and its Service "
        f"{'answers' if _repond(host) else 'does not answer'}. Expected 2 replicas on the last good image, "
        "answering on its Service.",
        fr=f"catalogue compte {disponibles} réplica(s) disponible(s), sur l'image {image or '?'}, et son "
        f"Service {'répond' if _repond(host) else 'ne répond pas'}. Attendu 2 réplicas sur la dernière bonne "
        "image, qui répondent sur leur Service.",
    )


# ----------------------------------------------------------------------
# 2. Le runbook remet le service après la même panne.
# ----------------------------------------------------------------------
def test_le_runbook_remet_le_service_apres_la_meme_panne(host, runbook):
    assert host.file(runbook).exists, message(
        en=f"No runbook at {runbook}.",
        fr=f"Aucun runbook en {runbook}.",
    )
    # La même panne que l'incident d'origine : une image qui n'existe pas.
    host.run(f"{ADMIN} -n {NS} set image deployment/catalogue nginx={MAUVAISE}")
    res = _jouer(host, runbook)
    host.run(f"{ADMIN} -n {NS} rollout status deployment/catalogue --timeout=120s")
    disponibles, image, _ = _etat(host)
    assert disponibles >= 2 and image == NG and _repond(host), message(
        en=f"After the same incident (image {MAUVAISE}), the runbook exits with {res.rc} and leaves "
        f"catalogue with {disponibles} available replica(s), on image {image or '?'}. Expected the service "
        f"back on the last good image. Runbook output: {(res.stdout + res.stderr).strip()[-200:]}",
        fr=f"Après la même panne (image {MAUVAISE}), le runbook sort en {res.rc} et laisse catalogue avec "
        f"{disponibles} réplica(s) disponible(s), sur l'image {image or '?'}. Attendu le service revenu sur "
        f"la dernière bonne image. Sortie du runbook : {(res.stdout + res.stderr).strip()[-200:]}",
    )


# ----------------------------------------------------------------------
# 3. Rejoué sur un service sain, le runbook sort en 0 et ne change rien.
# ----------------------------------------------------------------------
def test_le_runbook_se_rejoue_sans_rien_abimer(host, runbook):
    assert host.file(runbook).exists, message(
        en=f"No runbook at {runbook}.",
        fr=f"Aucun runbook en {runbook}.",
    )
    host.run(f"{ADMIN} -n {NS} rollout status deployment/catalogue --timeout=120s")
    avant = _etat(host)
    res = _jouer(host, runbook)
    apres = _etat(host)
    assert res.rc == 0 and apres == avant and _repond(host), message(
        en=f"Replayed on a service that works, the runbook exits with {res.rc}, and catalogue goes from "
        f"revision {avant[2] or '?'} ({avant[1] or '?'}) to revision {apres[2] or '?'} ({apres[1] or '?'}). "
        "Expected exit 0 and nothing changed: a runbook checks the state before acting.",
        fr=f"Rejoué sur un service qui marche, le runbook sort en {res.rc}, et catalogue passe de la "
        f"révision {avant[2] or '?'} ({avant[1] or '?'}) à la révision {apres[2] or '?'} ({apres[1] or '?'}). "
        "Attendu une sortie en 0 et rien de changé : un runbook regarde l'état avant d'agir.",
    )


# ----------------------------------------------------------------------
# 4. Le SLI sur 30 jours et le SLO sont consignés.
# ----------------------------------------------------------------------
def test_le_sli_et_le_slo_sont_consignes(host, memoire):
    attendu = round((memoire["total"] - memoire["ko"]) / memoire["total"] * 100, 2)
    donnees = _consigne(host)
    try:
        sli, slo = float(donnees.get("sli", "").replace(",", ".")), float(donnees.get("slo", "").replace(",", "."))
    except ValueError:
        sli = slo = None
    assert sli is not None and abs(sli - attendu) <= 0.01 and slo == SLO, message(
        en=f"The ConfigMap slo-catalogue gives sli={donnees.get('sli', '?')} and slo={donnees.get('slo', '?')}. "
        "Expected the availability over the 30 days of the probe journal, as a percentage with two decimals, "
        f"and the objective of {SLO}.",
        fr=f"Le ConfigMap slo-catalogue donne sli={donnees.get('sli', '?')} et slo={donnees.get('slo', '?')}. "
        "Attendu la disponibilité sur les 30 jours du journal de la sonde, en pourcentage à deux décimales, "
        f"et l'objectif de {SLO}.",
    )


# ----------------------------------------------------------------------
# 5. Le budget d'erreur restant est juste.
# ----------------------------------------------------------------------
def test_le_budget_d_erreur_restant_est_juste(host, memoire):
    budget = memoire["total"] * (100 - SLO) / 100
    attendu = round(budget - memoire["ko"])
    donnees = _consigne(host)
    try:
        lu = int(donnees.get("budget-restant", ""))
    except ValueError:
        lu = None
    assert lu == attendu, message(
        en=f"The ConfigMap slo-catalogue gives budget-restant={donnees.get('budget-restant', '?')}. Expected "
        "the error budget of the 30-day window, minus the minutes of outage, in whole minutes: it can be "
        "negative when the budget is overspent.",
        fr=f"Le ConfigMap slo-catalogue donne budget-restant={donnees.get('budget-restant', '?')}. Attendu le "
        "budget d'erreur de la fenêtre de 30 jours, moins les minutes de panne, en minutes entières : il peut "
        "être négatif quand le budget est dépassé.",
    )
