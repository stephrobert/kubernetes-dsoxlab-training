"""test_functional.py : ckad-job-cronjob

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Quatre affirmations. La première lit le spec du Job ; la deuxième son
résultat ; la troisième lit les horodatages de ses Pods, et c'est elle qui
prouve que deux exécutions ont réellement tourné en même temps, ce qu'un
parallelism déclaré ne garantit pas s'il est ignoré. La quatrième lit le
CronJob.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import pytest

from conftest import lab_host, lab_target_host, message

NAMESPACE = "lab"
JOB = "batch-job"
CRONJOB = "log-cleanup"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


def _instant(texte: str) -> datetime:
    return datetime.strptime(texte, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


# ----------------------------------------------------------------------
# 1. Le Job demande quatre complétions, deux à la fois.
# ----------------------------------------------------------------------
def test_le_job_demande_quatre_completions_deux_a_la_fois(host):
    job = _json(host, f"-n {NAMESPACE} get job {JOB}", message(
            en=f"No Job {JOB} in {NAMESPACE}.",
            fr=f"Aucun Job {JOB} dans {NAMESPACE}.",
        ))
    spec = job["spec"]
    assert spec.get("completions") == 4, message(
        en=f"completions is {spec.get('completions')!r}, expected 4: that is the number of "
        "successes the Job must reach.",
        fr=f"completions vaut {spec.get('completions')!r}, attendu 4 : c'est le nombre de "
        "réussites que le Job doit atteindre.",
    )
    assert spec.get("parallelism") == 2, message(
        en=f"parallelism is {spec.get('parallelism')!r}, expected 2: that is the number "
        "of simultaneous runs, and the database behind it supports no more.",
        fr=f"parallelism vaut {spec.get('parallelism')!r}, attendu 2 : c'est le nombre "
        "d'exécutions simultanées, et la base derrière n'en supporte pas plus.",
    )


# ----------------------------------------------------------------------
# 2. Le Job a réussi.
# ----------------------------------------------------------------------
def test_le_job_a_reussi(host):
    job = {}
    for _ in range(24):
        job = _json(host, f"-n {NAMESPACE} get job {JOB}", message(
            en=f"No Job {JOB} in {NAMESPACE}.",
            fr=f"Aucun Job {JOB} dans {NAMESPACE}.",
        ))
        if job["status"].get("succeeded", 0) >= 4:
            break
        time.sleep(5)
    assert job["status"].get("succeeded", 0) == 4, message(
        en=f"{job['status'].get('succeeded', 0)} success(es) out of 4 after two minutes. "
        f"Failures: {job['status'].get('failed', 0)}. A Job Pod that exits with an error "
        "does not count: look at kubectl get pods -l job-name=batch-job and their logs.",
        fr=f"{job['status'].get('succeeded', 0)} réussite(s) sur 4 après deux minutes. "
        f"Échecs : {job['status'].get('failed', 0)}. Un Pod de Job qui sort en erreur "
        "ne compte pas : regardez kubectl get pods -l job-name=batch-job et leurs logs.",
    )
    conditions = {c["type"]: c["status"] for c in job["status"].get("conditions") or []}
    assert conditions.get("Complete") == "True", message(
        en=f"The Job does not have the Complete condition: {conditions}",
        fr=f"Le Job n'a pas la condition Complete : {conditions}",
    )


# ----------------------------------------------------------------------
# 3. La preuve du parallélisme : deux Pods se sont chevauchés.
# ----------------------------------------------------------------------
def test_deux_executions_se_sont_chevauchees(host):
    pods = _json(host, f"-n {NAMESPACE} get pods -l job-name={JOB}", message(
            en="Cannot read the Job's Pods.",
            fr="Lecture des Pods du Job impossible.",
        ))["items"]
    reussis = [p for p in pods if p["status"].get("phase") == "Succeeded"]
    assert len(reussis) >= 4, message(
        en=f"{len(reussis)} Succeeded Pod(s) for the Job, 4 expected: the Pods of a finished "
        "Job remain, with their timestamps. If they are missing, the Job was "
        "recreated or its Pods deleted.",
        fr=f"{len(reussis)} Pod(s) Succeeded pour le Job, attendus 4 : les Pods d'un Job "
        "terminé restent, avec leurs horodatages. S'ils manquent, le Job a été "
        "recréé ou ses Pods supprimés.",
    )
    fenetres = []
    for p in reussis:
        etat = ((p["status"].get("containerStatuses") or [{}])[0].get("state") or {}).get("terminated") or {}
        if etat.get("startedAt") and etat.get("finishedAt"):
            fenetres.append((_instant(etat["startedAt"]), _instant(etat["finishedAt"]), p["metadata"]["name"]))
    assert len(fenetres) >= 4, message(
        en="The Pods' completion timestamps are incomplete.",
        fr="Les horodatages de fin des Pods sont incomplets.",
    )
    durees = [(fin - debut).total_seconds() for debut, fin, _ in fenetres]
    assert min(durees) >= 8, message(
        en=f"One run lasted {min(durees):.0f} s: the task must last at least "
        "ten seconds, otherwise nothing can overlap and nothing is measured.",
        fr=f"Une exécution a duré {min(durees):.0f} s : le traitement doit durer au moins "
        "dix secondes, sinon rien ne peut se chevaucher et rien ne se mesure.",
    )
    chevauchements = [
        (a[2], b[2]) for i, a in enumerate(fenetres) for b in fenetres[i + 1:]
        if a[0] < b[1] and b[0] < a[1]
    ]
    assert chevauchements, message(
        en="No pair of Pods overlapped in time: the four runs "
        "followed one another one by one. parallelism 2 declared, but not "
        f"observed. Windows: {[(n, d.strftime('%H:%M:%S'), f.strftime('%H:%M:%S')) for d, f, n in fenetres]}",
        fr="Aucune paire de Pods ne s'est chevauchée dans le temps : les quatre "
        "exécutions se sont suivies une à une. parallelism 2 déclaré, mais pas "
        f"observé. Fenêtres : {[(n, d.strftime('%H:%M:%S'), f.strftime('%H:%M:%S')) for d, f, n in fenetres]}",
    )


# ----------------------------------------------------------------------
# 4. Le CronJob est planifié, avec son historique borné.
# ----------------------------------------------------------------------
def test_le_cronjob_est_planifie_avec_historique_borne(host):
    cj = _json(host, f"-n {NAMESPACE} get cronjob {CRONJOB}", message(
            en=f"No CronJob {CRONJOB} in {NAMESPACE}.",
            fr=f"Aucun CronJob {CRONJOB} dans {NAMESPACE}.",
        ))
    spec = cj["spec"]
    assert spec.get("schedule", "").replace(" ", "") == "*/5****", message(
        en=f"schedule is {spec.get('schedule')!r}, expected '*/5 * * * *': every five minutes.",
        fr=f"schedule vaut {spec.get('schedule')!r}, attendu '*/5 * * * *' : toutes les cinq minutes.",
    )
    assert spec.get("successfulJobsHistoryLimit") == 3, message(
        en=f"successfulJobsHistoryLimit is {spec.get('successfulJobsHistoryLimit')!r}, expected 3.",
        fr=f"successfulJobsHistoryLimit vaut {spec.get('successfulJobsHistoryLimit')!r}, attendu 3.",
    )
    assert spec.get("failedJobsHistoryLimit") == 1, message(
        en=f"failedJobsHistoryLimit is {spec.get('failedJobsHistoryLimit')!r}, expected 1.",
        fr=f"failedJobsHistoryLimit vaut {spec.get('failedJobsHistoryLimit')!r}, attendu 1.",
    )
    conteneurs = spec["jobTemplate"]["spec"]["template"]["spec"].get("containers") or []
    assert conteneurs and "busybox" in conteneurs[0].get("image", ""), message(
        en=f"The CronJob must run busybox:1.36: image {conteneurs[0].get('image') if conteneurs else 'none'!r}.",
        fr=f"Le CronJob doit lancer busybox:1.36 : image {conteneurs[0].get('image') if conteneurs else 'aucune'!r}.",
    )
