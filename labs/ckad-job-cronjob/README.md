# A Job with parallel completions, and a CronJob

A **Job** starts Pods that do a task then stop. A **CronJob** creates Jobs on a
schedule. In this course, you start a simple Job, then a Job that must succeed
several times with several Pods at once, you see what a failing Job does, you
create a CronJob, you start it by hand, then you pause it.

You work in a scratch namespace, `essai-lots`, with the `bonjour`,
`traitement` ("processing") and `fragile` Jobs, and the `releve` ("reading")
CronJob. The challenge will ask you for other settings, in another namespace:
you will do it on your own, at the end.

Related page: [Jobs and CronJobs](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/jobs-and-cronjobs/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-job-cronjob
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a simple Job

Create the scratch namespace, then a `bonjour` Job. Everything after `--` is
the container's command:

```bash
kubectl create namespace essai-lots
kubectl create job bonjour --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-lots -- sh -c 'echo bonjour depuis un Job; sleep 2'
```

```text
namespace/essai-lots created
job.batch/bonjour created
```

Wait for it to end, then look at the Job and its Pod:

```bash
kubectl wait --for=condition=complete job/bonjour -n essai-lots --timeout=60s; kubectl get job bonjour -n essai-lots; kubectl get pods -n essai-lots -l job-name=bonjour
```

```text
job.batch/bonjour condition met
NAME      STATUS     COMPLETIONS   DURATION   AGE
bonjour   Complete   1/1           6s         6s
NAME            READY   STATUS      RESTARTS   AGE
bonjour-dvklt   0/1     Completed   0          6s
```

`1/1`: one success out of one requested. The Pod stays after the end, in
`Completed`, which lets you read what it wrote ("hello from a Job"):

```bash
kubectl logs job/bonjour -n essai-lots
```

```text
bonjour depuis un Job
```

Here are the settings `kubectl create job` used by default:

```bash
kubectl get job bonjour -n essai-lots -o jsonpath='completions={.spec.completions} parallelism={.spec.parallelism} backoffLimit={.spec.backoffLimit} restartPolicy={.spec.template.spec.restartPolicy}{"\n"}'
```

```text
completions=1 parallelism=1 backoffLimit=6 restartPolicy=Never
```

- `completions`: how many times the Job must succeed;
- `parallelism`: how many Pods may run at the same time;
- `backoffLimit`: how many new tries after a failure;
- `restartPolicy: Never`: a failed Pod is not restarted, the Job creates
  another one. A Job never accepts `Always`.

## 📚 Exercise 2: several completions, several at a time

`kubectl create job` has no option for `completions` and `parallelism`.
Generate the YAML, then add them under `spec` with `sed`: 6 successes, 3 Pods
at a time, and 5 seconds of work:

```bash
kubectl create job traitement --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-lots --dry-run=client -o yaml -- sh -c 'echo traitement de $HOSTNAME; sleep 5' | sed 's/^spec:/spec:\n  completions: 6\n  parallelism: 3/' > ~/traitement.yaml; grep -E '^spec:|completions|parallelism' ~/traitement.yaml
```

```text
spec:
  completions: 6
  parallelism: 3
```

Apply the file, and look at the Pods 3 seconds later:

```bash
kubectl apply -f ~/traitement.yaml -n essai-lots; sleep 3; kubectl get pods -n essai-lots -l job-name=traitement
```

```text
job.batch/traitement created
NAME               READY   STATUS    RESTARTS   AGE
traitement-6bqjb   1/1     Running   0          3s
traitement-b5wwd   1/1     Running   0          3s
traitement-s25jc   1/1     Running   0          3s
```

Three Pods run, no more. Wait for the Job to end:

```bash
kubectl wait --for=condition=complete job/traitement -n essai-lots --timeout=120s; kubectl get job traitement -n essai-lots
```

```text
job.batch/traitement condition met
NAME         STATUS     COMPLETIONS   DURATION   AGE
traitement   Complete   6/6           17s        17s
```

How do you prove that Pods ran **at the same time**? By their start and end
dates (`DEBUT` and `FIN`), sorted by start:

```bash
kubectl get pods -n essai-lots -l job-name=traitement --sort-by=.status.startTime -o custom-columns=POD:.metadata.name,ETAT:.status.phase,DEBUT:.status.startTime,FIN:.status.containerStatuses[0].state.terminated.finishedAt
```

```text
POD                ETAT        DEBUT                  FIN
traitement-6bqjb   Succeeded   2026-11-19T21:04:30Z   2026-11-19T21:04:36Z
traitement-b5wwd   Succeeded   2026-11-19T21:04:30Z   2026-11-19T21:04:36Z
traitement-s25jc   Succeeded   2026-11-19T21:04:30Z   2026-11-19T21:04:36Z
traitement-gz77g   Succeeded   2026-11-19T21:04:39Z   2026-11-19T21:04:45Z
traitement-h9qrt   Succeeded   2026-11-19T21:04:39Z   2026-11-19T21:04:45Z
traitement-tffp4   Succeeded   2026-11-19T21:04:39Z   2026-11-19T21:04:44Z
```

Two waves of three: the first three Pods start and end together, the next
three start when the first ones have finished. The Job succeeded six times
without ever going over three Pods at a time.

## 📚 Exercise 3: a Job that fails

Create a `fragile` Job that fails every time (`exit 1`), with only 2 new tries
(`backoffLimit: 2`):

```bash
kubectl create job fragile --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-lots --dry-run=client -o yaml -- sh -c 'echo tentative; exit 1' | sed 's/^spec:/spec:\n  backoffLimit: 2/' | kubectl apply -f - -n essai-lots
```

```text
job.batch/fragile created
```

Wait until it is declared failed:

```bash
kubectl wait --for=condition=failed job/fragile -n essai-lots --timeout=180s; kubectl get job fragile -n essai-lots; kubectl get pods -n essai-lots -l job-name=fragile
```

```text
job.batch/fragile condition met
NAME      STATUS   COMPLETIONS   DURATION   AGE
fragile   Failed   0/1           34s        34s
NAME            READY   STATUS   RESTARTS   AGE
fragile-5pt9m   0/1     Error    0          3s
fragile-dg6ks   0/1     Error    0          34s
fragile-hx9xm   0/1     Error    0          23s
```

Three Pods: the first try, then the 2 new tries allowed. Look at their age
(34 s, 23 s, 3 s): Kubernetes waits longer and longer between two tries. The
Job's conditions give the reason for the failure:

```bash
kubectl get job fragile -n essai-lots -o jsonpath='{range .status.conditions[*]}{.type} {.reason}{"\n"}{end}'
```

```text
FailureTarget BackoffLimitExceeded
Failed BackoffLimitExceeded
```

`BackoffLimitExceeded`: the limit of new tries is exceeded.

## 📚 Exercise 4: a CronJob

Create a `releve` CronJob, started every 10 minutes. The schedule is written
in cron format: `*/10 * * * *` means "every 10 minutes". `sed` adds two
history limits: keep the last 2 successful Jobs and the last failed Job:

```bash
kubectl create cronjob releve --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --schedule='*/10 * * * *' -n essai-lots --dry-run=client -o yaml -- sh -c 'echo releve du $(date)' | sed 's/^spec:/spec:\n  successfulJobsHistoryLimit: 2\n  failedJobsHistoryLimit: 1/' | kubectl apply -f - -n essai-lots
```

```text
cronjob.batch/releve created
```

```bash
kubectl get cronjob releve -n essai-lots
kubectl get cronjob releve -n essai-lots -o jsonpath='schedule={.spec.schedule} reussis={.spec.successfulJobsHistoryLimit} echoues={.spec.failedJobsHistoryLimit}{"\n"}'
```

```text
NAME     SCHEDULE       TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
releve   */10 * * * *   <none>     False     0        <none>          0s
schedule=*/10 * * * * reussis=2 echoues=1
```

`LAST SCHEDULE <none>`: the CronJob has not started anything yet. It waits for
its next due time, which may be 10 minutes away.

## 📚 Exercise 5: start the CronJob by hand

To try it without waiting, create a Job **from** the CronJob, with `--from`:

```bash
kubectl create job releve-manuel --from=cronjob/releve -n essai-lots
kubectl wait --for=condition=complete job/releve-manuel -n essai-lots --timeout=60s; kubectl logs job/releve-manuel -n essai-lots
```

```text
job.batch/releve-manuel created
job.batch/releve-manuel condition met
releve du Thu Nov 19 21:05:21 UTC 2026
```

The Job took the CronJob's template and ran right away. It keeps a record of
where it came from:

```bash
kubectl get job releve-manuel -n essai-lots -o jsonpath='{.metadata.annotations}{"\n"}{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
```

```text
{"cronjob.kubernetes.io/instantiate":"manual"}
CronJob/releve
```

The annotation says it was started by hand, and its owner is the `releve`
CronJob.

## 📚 Exercise 6: suspend a CronJob

`suspend: true` pauses a CronJob: it starts nothing more until you set it back
to `false`.

```bash
kubectl patch cronjob releve -n essai-lots -p '{"spec":{"suspend":true}}'; kubectl get cronjob releve -n essai-lots
```

```text
cronjob.batch/releve patched
NAME     SCHEDULE       TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
releve   */10 * * * *   <none>     True      0        <none>          3s
```

`SUSPEND True`: the CronJob is paused.

## 🧹 Clean up

Delete the scratch namespace and the work file:

```bash
kubectl delete namespace essai-lots; rm -f ~/traitement.yaml
```

```text
namespace "essai-lots" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-job-cronjob
dsoxlab check ckad-job-cronjob
```

```text
╭──── Result: ckad-job-cronjob ─────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another Job, with its own numbers of
successes and Pods at a time, and another CronJob, also to start by hand.

```bash
dsoxlab run ckad-job-cronjob
dsoxlab challenge ckad-job-cronjob
```
