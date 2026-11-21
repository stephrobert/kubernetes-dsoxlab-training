"""test_functional.py : k8s-challenge-executer-et-planifier-des-taches

Ces tests lisent l'état du cluster, jamais les commandes tapées.

La préparation tire au sort le nombre de lots (3 à 6), leurs noms et la
période d'export, et les garde dans une mémoire lisible par root seulement.
Le Job facturer-lots doit donc avoir autant de complétions que de lots, et
chacun de ses Pods doit avoir traité le lot de son propre index : un Job
recopié de la leçon (quatre complétions, aucun index) ne passe pas.

Deux tests sont bloquants, parce qu'ils portent le cœur du geste : un Job
indexé qui traite chaque lot une fois, et un CronJob planifié comme demandé.

Tous échouent avant le travail : ni facturer-lots, ni relance-impayes, ni
Job lancé à la main n'existent, et export-compta est en échec.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from conftest import lab_host, lab_target_host, message

NS = "compta"
JOB, CRONJOB, EXPORT = "facturer-lots", "relance-impayes", "export-compta"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MEMOIRE = "/var/lib/dsoxlab/challenge-executer-et-planifier-des-taches.json"
LIGNE = re.compile(r"lot\s+(\d+)\s*:\s*(\S+)")
ATTENTE = 120
PAS = 5
NA_PAS = "n'a pas"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


@pytest.fixture(scope="module")
def memoire(host) -> dict:
    res = host.run(f"sudo cat {MEMOIRE}")
    if res.rc != 0:
        pytest.fail(message(
            en="The memory of the preparation is missing: `dsoxlab reset` sets the situation back.",
            fr="La mémoire de la préparation manque : `dsoxlab reset` repose la situation.",
        ))
    return json.loads(res.stdout)


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _termine(job: dict | None) -> bool:
    for c in ((job or {}).get("status") or {}).get("conditions") or []:
        if c.get("type") in ("Complete", "Failed") and c.get("status") == "True":
            return True
    return False


def _complet(job: dict | None) -> bool:
    return any(c.get("type") == "Complete" and c.get("status") == "True"
               for c in ((job or {}).get("status") or {}).get("conditions") or [])


def _attendre_job(host, nom: str) -> dict | None:
    job = _json(host, f"-n {NS} get job {nom}")
    fin = time.monotonic() + ATTENTE
    while job is not None and not _termine(job) and time.monotonic() < fin:
        time.sleep(PAS)
        job = _json(host, f"-n {NS} get job {nom}") or job
    return job


# ----------------------------------------------------------------------
# 1. facturer-lots traite chaque lot une fois, par son index. BLOQUANT.
# ----------------------------------------------------------------------
def test_facturer_lots_traite_chaque_lot_une_fois(host, memoire):
    lots = memoire["lots"]
    job = _attendre_job(host, JOB)
    assert job is not None, message(
        en=f"No Job {JOB} in {NS}.",
        fr=f"Aucun Job {JOB} dans {NS}.",
    )
    spec, statut = job.get("spec") or {}, job.get("status") or {}
    assert spec.get("completionMode") == "Indexed" and spec.get("completions") == len(lots) \
            and _complet(job) and statut.get("succeeded") == len(lots), message(
        en=f"{JOB} is in mode {spec.get('completionMode')!r}, asks for {spec.get('completions')!r} completion(s) "
        f"and counts {statut.get('succeeded', 0)} success(es). Expected: an indexed Job, as many completions as "
        f"there are lots in the ConfigMap lots ({len(lots)}), all succeeded.",
        fr=f"{JOB} est en mode {spec.get('completionMode')!r}, demande {spec.get('completions')!r} complétion(s) "
        f"et compte {statut.get('succeeded', 0)} réussite(s). Attendu : un Job indexé, autant de complétions que "
        f"de lots dans la ConfigMap lots ({len(lots)}), toutes réussies.",
    )
    pods = _json(host, f"-n {NS} get pods -l job-name={JOB} --field-selector status.phase=Succeeded") or {}
    traites: dict[int, str] = {}
    for pod in pods.get("items", []):
        index = (pod["metadata"].get("labels") or {}).get("batch.kubernetes.io/job-completion-index")
        journal = host.run(f"{ADMIN} -n {NS} logs {pod['metadata']['name']}").stdout
        for numero, nom in LIGNE.findall(journal):
            if index is not None and numero == index:
                traites[int(numero)] = nom
    attendu = dict(enumerate(lots))
    assert traites == attendu, message(
        en=f"The Pods of {JOB} report {traites or 'no lot'}. Expected each Pod to write `lot <index> : <name>` "
        "for the lot of its own index, every lot once.",
        fr=f"Les Pods de {JOB} annoncent {traites or 'aucun lot'}. Attendu : chaque Pod écrit `lot <index> : <nom>` "
        "pour le lot de son propre index, chaque lot une fois.",
    )


# ----------------------------------------------------------------------
# 2. facturer-lots respecte le parallélisme et la limite de reprises.
# ----------------------------------------------------------------------
def test_facturer_lots_respecte_le_parallelisme_et_les_reprises(host):
    spec = (_json(host, f"-n {NS} get job {JOB}") or {}).get("spec") or {}
    vu = (spec.get("parallelism"), spec.get("backoffLimit"))
    assert vu == (2, 1), message(
        en=f"{JOB} runs {vu[0]!r} Pod(s) at a time and allows {vu[1]!r} retry(ies). Expected 2 and 1.",
        fr=f"{JOB} fait tourner {vu[0]!r} Pod(s) à la fois et accorde {vu[1]!r} reprise(s). Attendu 2 et 1.",
    )


# ----------------------------------------------------------------------
# 3. relance-impayes est planifié comme demandé. BLOQUANT.
# ----------------------------------------------------------------------
def test_relance_impayes_est_planifie_comme_demande(host):
    cj = _json(host, f"-n {NS} get cronjob {CRONJOB}")
    assert cj is not None, message(
        en=f"No CronJob {CRONJOB} in {NS}.",
        fr=f"Aucun CronJob {CRONJOB} dans {NS}.",
    )
    spec = cj.get("spec") or {}
    vu = {
        "planning": spec.get("schedule", "").split(),
        "fuseau": spec.get("timeZone"),
        "concurrence": spec.get("concurrencyPolicy"),
        "historique": (spec.get("successfulJobsHistoryLimit"), spec.get("failedJobsHistoryLimit")),
        "retard": spec.get("startingDeadlineSeconds"),
        "suspendu": spec.get("suspend", False),
    }
    attendu = {
        "planning": ["15", "6", "*", "*", "1-5"],
        "fuseau": "Europe/Paris",
        "concurrence": "Replace",
        "historique": (3, 2),
        "retard": 300,
        "suspendu": False,
    }
    ecarts = {k: vu[k] for k in attendu if vu[k] != attendu[k]}
    assert not ecarts, message(
        en=f"{CRONJOB} differs from the request on: {ecarts}. Expected Monday to Friday at 6:15, Paris time, a new "
        "run replacing one still running, three successful and two failed Jobs kept, at most five minutes late, "
        "active.",
        fr=f"{CRONJOB} s'écarte de la demande sur : {ecarts}. Attendu du lundi au vendredi à 6 h 15, heure de Paris, "
        "une nouvelle exécution qui remplace celle encore en cours, trois Jobs réussis et deux échoués conservés, "
        "au plus cinq minutes de retard, actif.",
    )


# ----------------------------------------------------------------------
# 4. Un Job lancé à la main depuis relance-impayes a réussi.
# ----------------------------------------------------------------------
def test_un_job_lance_a_la_main_depuis_relance_impayes_a_reussi(host):
    jobs = (_json(host, f"-n {NS} get jobs") or {}).get("items", [])
    issus = [j for j in jobs if any(r.get("kind") == "CronJob" and r.get("name") == CRONJOB
                                    for r in j["metadata"].get("ownerReferences") or [])]
    fin = time.monotonic() + ATTENTE
    while issus and not any(_complet(j) for j in issus) and time.monotonic() < fin:
        time.sleep(PAS)
        issus = [_json(host, f"-n {NS} get job {j['metadata']['name']}") or j for j in issus]
    assert any(_complet(j) for j in issus), message(
        en=f"No Job created from {CRONJOB} has completed (Jobs it owns: "
        f"{[j['metadata']['name'] for j in issus] or 'none'}). A run must be started by hand, without waiting for "
        "the schedule.",
        fr=f"Aucun Job issu de {CRONJOB} n'a réussi (Jobs qui lui appartiennent : "
        f"{[j['metadata']['name'] for j in issus] or 'aucun'}). Une exécution doit être lancée à la main, sans "
        "attendre le planning.",
    )


# ----------------------------------------------------------------------
# 5. export-compta, recréé avec sa configuration, a réussi.
# ----------------------------------------------------------------------
def test_export_compta_relance_avec_sa_configuration_a_reussi(host, memoire):
    job = _attendre_job(host, EXPORT)
    assert job is not None, message(
        en=f"No Job {EXPORT} in {NS}.",
        fr=f"Aucun Job {EXPORT} dans {NS}.",
    )
    recree = job["metadata"]["uid"] != memoire["uid_export"]
    gabarit = json.dumps(job["spec"]["template"]["spec"].get("containers") or [])
    relie = "export-config" in gabarit
    journal = host.run(f"{ADMIN} -n {NS} logs job/{EXPORT}").stdout
    assert recree and relie and _complet(job) and memoire["periode"] in journal, message(
        en=f"{EXPORT} {'was' if recree else 'was not'} recreated, {'reads' if relie else 'does not read'} the "
        f"ConfigMap export-config, and {'has' if _complet(job) else 'has not'} completed. Expected the Job "
        "recreated with this configuration, and a run that exports the period it holds.",
        fr=f"{EXPORT} {'a' if recree else NA_PAS} été recréé, {'lit' if relie else 'ne lit pas'} la ConfigMap "
        f"export-config, et {'a' if _complet(job) else NA_PAS} réussi. Attendu : le Job recréé avec cette "
        "configuration, et une exécution qui exporte la période qu'elle porte.",
    )
