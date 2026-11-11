"""test_functional.py : ckad-job-cronjob

Ces tests lisent l'état du cluster, jamais les commandes tapées. Un test
vérifie un seul état demandé par l'énoncé.

Le parallélisme se prouve par les horodatages des Pods du Job : un parallelism
déclaré ne garantit pas que deux exécutions ont tourné en même temps. Le
déclenchement à la main se reconnaît à l'annotation que pose
`kubectl create job --from` et au lien de propriété vers le CronJob.

Tous échouent avant le travail : ni batch-job ni log-cleanup n'existent.
L'attente de fin d'un Job ne s'ouvre que s'il existe déjà.

Les messages disent ce qui manque, jamais la commande qui le pose.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import pytest

from conftest import lab_host, lab_target_host, message

NS = "lab"
JOB = "batch-job"
CRONJOB = "log-cleanup"
IMAGE = "busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
ADMIN = "sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
ATTENTE = 120
PAS = 5


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _json(host, args: str) -> dict | None:
    res = host.run(f"{ADMIN} {args} -o json")
    if res.rc != 0 or not res.stdout.strip():
        return None
    return json.loads(res.stdout)


def _instant(texte: str) -> datetime:
    return datetime.strptime(texte, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _complet(job: dict) -> bool:
    return any(c.get("type") == "Complete" and c.get("status") == "True"
               for c in (job.get("status") or {}).get("conditions") or [])


def _attendre_job(host, nom: str) -> dict | None:
    job = _json(host, f"-n {NS} get job {nom}")
    fin = time.monotonic() + ATTENTE
    while job is not None and not _complet(job) and time.monotonic() < fin:
        time.sleep(PAS)
        job = _json(host, f"-n {NS} get job {nom}") or job
    return job


# ----------------------------------------------------------------------
# 1. Le Job demande quatre complétions, deux à la fois, sur l'image demandée.
# ----------------------------------------------------------------------
def test_batch_job_demande_quatre_completions_deux_a_la_fois(host):
    job = _json(host, f"-n {NS} get job {JOB}")
    assert job is not None, message(en=f"No Job {JOB} in {NS}.", fr=f"Aucun Job {JOB} dans {NS}.")
    spec = job["spec"]
    image = (spec["template"]["spec"].get("containers") or [{}])[0].get("image")
    assert spec.get("completions") == 4 and spec.get("parallelism") == 2 and image == IMAGE, message(
        en=f"{JOB} asks for completions={spec.get('completions')!r} and parallelism="
        f"{spec.get('parallelism')!r}, on {image!r}. Expected 4 successes, 2 at a time, on the image of "
        "the requirements pinned by digest.",
        fr=f"{JOB} demande completions={spec.get('completions')!r} et parallelism="
        f"{spec.get('parallelism')!r}, sur {image!r}. Attendu 4 réussites, 2 à la fois, sur l'image du "
        "cahier des charges épinglée par digest.",
    )


# ----------------------------------------------------------------------
# 2. Le Job est terminé avec succès.
# ----------------------------------------------------------------------
def test_batch_job_est_termine_avec_succes(host):
    job = _attendre_job(host, JOB)
    assert job is not None, message(en=f"No Job {JOB} in {NS}.", fr=f"Aucun Job {JOB} dans {NS}.")
    s = job.get("status") or {}
    assert _complet(job) and s.get("succeeded", 0) == 4, message(
        en=f"{JOB} counts {s.get('succeeded', 0)} success(es) and {s.get('failed', 0)} failure(s) after "
        f"{ATTENTE}s, without the Complete condition. A Job Pod that exits with an error does not count.",
        fr=f"{JOB} compte {s.get('succeeded', 0)} réussite(s) et {s.get('failed', 0)} échec(s) après "
        f"{ATTENTE}s, sans la condition Complete. Un Pod de Job qui sort en erreur ne compte pas.",
    )


# ----------------------------------------------------------------------
# 3. Deux exécutions se sont réellement chevauchées.
# ----------------------------------------------------------------------
def test_deux_executions_se_sont_chevauchees(host):
    _attendre_job(host, JOB)
    pods = (_json(host, f"-n {NS} get pods -l job-name={JOB}") or {}).get("items", [])
    fenetres = []
    for p in pods:
        if p["status"].get("phase") != "Succeeded":
            continue
        etat = ((p["status"].get("containerStatuses") or [{}])[0].get("state") or {}).get("terminated") or {}
        if etat.get("startedAt") and etat.get("finishedAt"):
            fenetres.append((_instant(etat["startedAt"]), _instant(etat["finishedAt"]), p["metadata"]["name"]))
    courtes = [n for d, f, n in fenetres if (f - d).total_seconds() < 8]
    chevauchements = [(a[2], b[2]) for i, a in enumerate(fenetres) for b in fenetres[i + 1:]
                      if a[0] < b[1] and b[0] < a[1]]
    assert len(fenetres) >= 4 and not courtes and chevauchements, message(
        en=f"{len(fenetres)} finished Pod(s) of {JOB} found, {len(courtes)} lasting under ten seconds, and "
        f"{len(chevauchements)} pair(s) overlapping in time. Expected the four Pods kept, each run lasting "
        "at least ten seconds, and two of them running at the same time.",
        fr=f"{len(fenetres)} Pod(s) terminé(s) de {JOB} trouvé(s), dont {len(courtes)} de moins de dix "
        f"secondes, et {len(chevauchements)} paire(s) chevauchée(s) dans le temps. Attendu les quatre Pods "
        "conservés, chaque exécution durant au moins dix secondes, et deux d'entre elles en même temps.",
    )


# ----------------------------------------------------------------------
# 4. Le CronJob est planifié toutes les cinq minutes, historique borné.
# ----------------------------------------------------------------------
def test_log_cleanup_est_planifie_avec_un_historique_borne(host):
    cj = _json(host, f"-n {NS} get cronjob {CRONJOB}")
    assert cj is not None, message(en=f"No CronJob {CRONJOB} in {NS}.", fr=f"Aucun CronJob {CRONJOB} dans {NS}.")
    spec = cj["spec"]
    image = (spec["jobTemplate"]["spec"]["template"]["spec"].get("containers") or [{}])[0].get("image")
    attendu = spec.get("schedule", "").split() == ["*/5", "*", "*", "*", "*"] \
        and spec.get("successfulJobsHistoryLimit") == 3 and spec.get("failedJobsHistoryLimit") == 1 \
        and image == IMAGE
    assert attendu, message(
        en=f"{CRONJOB} has schedule {spec.get('schedule')!r}, keeps {spec.get('successfulJobsHistoryLimit')!r} "
        f"successful and {spec.get('failedJobsHistoryLimit')!r} failed Job(s), on {image!r}. Expected every "
        "five minutes, three successful and one failed, on the image of the requirements.",
        fr=f"{CRONJOB} a pour planning {spec.get('schedule')!r}, garde {spec.get('successfulJobsHistoryLimit')!r} "
        f"Job(s) réussi(s) et {spec.get('failedJobsHistoryLimit')!r} échoué(s), sur {image!r}. Attendu toutes "
        "les cinq minutes, trois réussis et un échoué, sur l'image du cahier des charges.",
    )


# ----------------------------------------------------------------------
# 5. Un Job lancé à la main depuis le CronJob a réussi.
# ----------------------------------------------------------------------
def test_un_job_lance_a_la_main_depuis_log_cleanup_a_reussi(host):
    jobs = (_json(host, f"-n {NS} get jobs") or {}).get("items", [])
    manuels = [
        j["metadata"]["name"] for j in jobs
        if (j["metadata"].get("annotations") or {}).get("cronjob.kubernetes.io/instantiate") == "manual"
        and any(o.get("kind") == "CronJob" and o.get("name") == CRONJOB
                for o in j["metadata"].get("ownerReferences") or [])
    ]
    assert manuels, message(
        en=f"No Job started by hand from the {CRONJOB} CronJob: its next run may be minutes away, and "
        "the requirements ask for a run now, from the CronJob itself.",
        fr=f"Aucun Job lancé à la main depuis le CronJob {CRONJOB} : sa prochaine échéance peut être dans "
        "plusieurs minutes, et le cahier des charges demande une exécution tout de suite, depuis le "
        "CronJob lui-même.",
    )
    job = _attendre_job(host, manuels[0])
    assert job is not None and _complet(job), message(
        en=f"The Job {manuels[0]} started by hand from {CRONJOB} has not succeeded.",
        fr=f"Le Job {manuels[0]} lancé à la main depuis {CRONJOB} n'a pas réussi.",
    )
