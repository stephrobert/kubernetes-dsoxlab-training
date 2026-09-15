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
from datetime import datetime, timezone

import pytest

from conftest import lab_host, lab_target_host

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
    return datetime.strptime(texte, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# ----------------------------------------------------------------------
# 1. Le Job demande quatre complétions, deux à la fois.
# ----------------------------------------------------------------------
def test_le_job_demande_quatre_completions_deux_a_la_fois(host):
    job = _json(host, f"-n {NAMESPACE} get job {JOB}", f"Aucun Job {JOB} dans {NAMESPACE}.")
    spec = job["spec"]
    assert spec.get("completions") == 4, (
        f"completions vaut {spec.get('completions')!r}, attendu 4 : c'est le nombre de "
        "réussites que le Job doit atteindre."
    )
    assert spec.get("parallelism") == 2, (
        f"parallelism vaut {spec.get('parallelism')!r}, attendu 2 : c'est le nombre "
        "d'exécutions simultanées, et la base derrière n'en supporte pas plus."
    )


# ----------------------------------------------------------------------
# 2. Le Job a réussi.
# ----------------------------------------------------------------------
def test_le_job_a_reussi(host):
    job = {}
    for _ in range(24):
        job = _json(host, f"-n {NAMESPACE} get job {JOB}", f"Aucun Job {JOB} dans {NAMESPACE}.")
        if job["status"].get("succeeded", 0) >= 4:
            break
        time.sleep(5)
    assert job["status"].get("succeeded", 0) == 4, (
        f"{job['status'].get('succeeded', 0)} réussite(s) sur 4 après deux minutes. "
        f"Échecs : {job['status'].get('failed', 0)}. Un Pod de Job qui sort en erreur "
        "ne compte pas : regardez kubectl get pods -l job-name=batch-job et leurs logs."
    )
    conditions = {c["type"]: c["status"] for c in job["status"].get("conditions") or []}
    assert conditions.get("Complete") == "True", f"Le Job n'a pas la condition Complete : {conditions}"


# ----------------------------------------------------------------------
# 3. La preuve du parallélisme : deux Pods se sont chevauchés.
# ----------------------------------------------------------------------
def test_deux_executions_se_sont_chevauchees(host):
    pods = _json(host, f"-n {NAMESPACE} get pods -l job-name={JOB}", "Lecture des Pods du Job impossible.")["items"]
    reussis = [p for p in pods if p["status"].get("phase") == "Succeeded"]
    assert len(reussis) >= 4, (
        f"{len(reussis)} Pod(s) Succeeded pour le Job, attendus 4 : les Pods d'un Job "
        "terminé restent, avec leurs horodatages. S'ils manquent, le Job a été "
        "recréé ou ses Pods supprimés."
    )
    fenetres = []
    for p in reussis:
        etat = ((p["status"].get("containerStatuses") or [{}])[0].get("state") or {}).get("terminated") or {}
        if etat.get("startedAt") and etat.get("finishedAt"):
            fenetres.append((_instant(etat["startedAt"]), _instant(etat["finishedAt"]), p["metadata"]["name"]))
    assert len(fenetres) >= 4, "Les horodatages de fin des Pods sont incomplets."
    durees = [(fin - debut).total_seconds() for debut, fin, _ in fenetres]
    assert min(durees) >= 8, (
        f"Une exécution a duré {min(durees):.0f} s : le traitement doit durer au moins "
        "dix secondes, sinon rien ne peut se chevaucher et rien ne se mesure."
    )
    chevauchements = [
        (a[2], b[2]) for i, a in enumerate(fenetres) for b in fenetres[i + 1:]
        if a[0] < b[1] and b[0] < a[1]
    ]
    assert chevauchements, (
        "Aucune paire de Pods ne s'est chevauchée dans le temps : les quatre "
        "exécutions se sont suivies une à une. parallelism 2 déclaré, mais pas "
        f"observé. Fenêtres : {[(n, d.strftime('%H:%M:%S'), f.strftime('%H:%M:%S')) for d, f, n in fenetres]}"
    )


# ----------------------------------------------------------------------
# 4. Le CronJob est planifié, avec son historique borné.
# ----------------------------------------------------------------------
def test_le_cronjob_est_planifie_avec_historique_borne(host):
    cj = _json(host, f"-n {NAMESPACE} get cronjob {CRONJOB}", f"Aucun CronJob {CRONJOB} dans {NAMESPACE}.")
    spec = cj["spec"]
    assert spec.get("schedule", "").replace(" ", "") == "*/5****", (
        f"schedule vaut {spec.get('schedule')!r}, attendu '*/5 * * * *' : toutes les cinq minutes."
    )
    assert spec.get("successfulJobsHistoryLimit") == 3, (
        f"successfulJobsHistoryLimit vaut {spec.get('successfulJobsHistoryLimit')!r}, attendu 3."
    )
    assert spec.get("failedJobsHistoryLimit") == 1, (
        f"failedJobsHistoryLimit vaut {spec.get('failedJobsHistoryLimit')!r}, attendu 1."
    )
    conteneurs = spec["jobTemplate"]["spec"]["template"]["spec"].get("containers") or []
    assert conteneurs and "busybox" in conteneurs[0].get("image", ""), (
        f"Le CronJob doit lancer busybox:1.36 : image {conteneurs[0].get('image') if conteneurs else 'aucune'!r}."
    )
