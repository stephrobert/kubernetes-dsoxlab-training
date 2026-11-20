# Un Job à complétions parallèles et un CronJob

Un **Job** lance des Pods qui font une tâche puis s'arrêtent. Un **CronJob**
crée des Jobs selon un calendrier. Dans ce cours, vous lancez un Job simple,
puis un Job qui doit réussir plusieurs fois avec plusieurs Pods en même temps,
vous voyez ce que fait un Job qui échoue, vous créez un CronJob, vous le lancez
à la main, puis vous le mettez en pause.

Vous travaillez dans un namespace d'essai, `essai-lots`, avec les Jobs
`bonjour`, `traitement` et `fragile`, et le CronJob `releve`. Le challenge vous
demandera d'autres réglages, dans un autre namespace : vous le ferez seul, à la
fin.

Page associée : [Jobs et CronJobs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-job-cronjob
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un Job simple

Créez le namespace d'essai, puis un Job `bonjour`. Tout ce qui suit `--` est
la commande du conteneur :

```bash
kubectl create namespace essai-lots
kubectl create job bonjour --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-lots -- sh -c 'echo bonjour depuis un Job; sleep 2'
```

```text
namespace/essai-lots created
job.batch/bonjour created
```

Attendez sa fin, puis regardez le Job et son Pod :

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

`1/1` : une réussite sur une demandée. Le Pod reste là après la fin, en
`Completed`, ce qui permet de lire ce qu'il a écrit :

```bash
kubectl logs job/bonjour -n essai-lots
```

```text
bonjour depuis un Job
```

Voici les réglages que `kubectl create job` a mis par défaut :

```bash
kubectl get job bonjour -n essai-lots -o jsonpath='completions={.spec.completions} parallelism={.spec.parallelism} backoffLimit={.spec.backoffLimit} restartPolicy={.spec.template.spec.restartPolicy}{"\n"}'
```

```text
completions=1 parallelism=1 backoffLimit=6 restartPolicy=Never
```

- `completions` : combien de fois le Job doit réussir ;
- `parallelism` : combien de Pods peuvent tourner en même temps ;
- `backoffLimit` : combien de nouveaux essais après un échec ;
- `restartPolicy: Never` : un Pod en échec n'est pas redémarré, le Job en crée
  un autre. Un Job n'accepte jamais `Always`.

## 📚 Exercice 2 : plusieurs complétions, plusieurs à la fois

`kubectl create job` n'a pas d'option pour `completions` et `parallelism`.
Générez le YAML, puis ajoutez-les sous `spec` avec `sed` : 6 réussites, 3 Pods
à la fois, et un travail de 5 secondes :

```bash
kubectl create job traitement --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-lots --dry-run=client -o yaml -- sh -c 'echo traitement de $HOSTNAME; sleep 5' | sed 's/^spec:/spec:\n  completions: 6\n  parallelism: 3/' > ~/traitement.yaml; grep -E '^spec:|completions|parallelism' ~/traitement.yaml
```

```text
spec:
  completions: 6
  parallelism: 3
```

Appliquez le fichier, et regardez les Pods 3 secondes plus tard :

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

Trois Pods tournent, pas plus. Attendez la fin du Job :

```bash
kubectl wait --for=condition=complete job/traitement -n essai-lots --timeout=120s; kubectl get job traitement -n essai-lots
```

```text
job.batch/traitement condition met
NAME         STATUS     COMPLETIONS   DURATION   AGE
traitement   Complete   6/6           17s        17s
```

Comment prouver que des Pods ont tourné **en même temps** ? Par leurs dates de
début et de fin, triées par début :

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

Deux vagues de trois : les trois premiers Pods démarrent et finissent
ensemble, les trois suivants démarrent quand les premiers ont fini. Le Job a
réussi six fois sans jamais dépasser trois Pods à la fois.

## 📚 Exercice 3 : un Job qui échoue

Créez un Job `fragile` qui échoue à chaque fois (`exit 1`), avec seulement
2 nouveaux essais (`backoffLimit: 2`) :

```bash
kubectl create job fragile --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-lots --dry-run=client -o yaml -- sh -c 'echo tentative; exit 1' | sed 's/^spec:/spec:\n  backoffLimit: 2/' | kubectl apply -f - -n essai-lots
```

```text
job.batch/fragile created
```

Attendez qu'il soit déclaré en échec :

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

Trois Pods : le premier essai, puis les 2 nouveaux essais permis. Regardez
leur âge (34 s, 23 s, 3 s) : Kubernetes attend de plus en plus longtemps entre
deux essais. Les conditions du Job donnent la raison de l'échec :

```bash
kubectl get job fragile -n essai-lots -o jsonpath='{range .status.conditions[*]}{.type} {.reason}{"\n"}{end}'
```

```text
FailureTarget BackoffLimitExceeded
Failed BackoffLimitExceeded
```

`BackoffLimitExceeded` : la limite de nouveaux essais est dépassée.

## 📚 Exercice 4 : un CronJob

Créez un CronJob `releve`, lancé toutes les 10 minutes. Le calendrier
s'écrit au format cron : `*/10 * * * *` veut dire « toutes les 10 minutes ».
`sed` ajoute deux limites d'historique : garder les 2 derniers Jobs réussis et
le dernier Job échoué :

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

`LAST SCHEDULE <none>` : le CronJob n'a encore rien lancé. Il attend sa
prochaine échéance, qui peut être dans 10 minutes.

## 📚 Exercice 5 : lancer le CronJob à la main

Pour l'essayer sans attendre, créez un Job **à partir** du CronJob, avec
`--from` :

```bash
kubectl create job releve-manuel --from=cronjob/releve -n essai-lots
kubectl wait --for=condition=complete job/releve-manuel -n essai-lots --timeout=60s; kubectl logs job/releve-manuel -n essai-lots
```

```text
job.batch/releve-manuel created
job.batch/releve-manuel condition met
releve du Thu Nov 19 21:05:21 UTC 2026
```

Le Job a pris le modèle du CronJob et s'est exécuté tout de suite. Il garde la
trace de son origine :

```bash
kubectl get job releve-manuel -n essai-lots -o jsonpath='{.metadata.annotations}{"\n"}{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
```

```text
{"cronjob.kubernetes.io/instantiate":"manual"}
CronJob/releve
```

L'annotation dit qu'il a été lancé à la main, et le propriétaire est le
CronJob `releve`.

## 📚 Exercice 6 : suspendre un CronJob

`suspend: true` met un CronJob en pause : il ne lancera plus rien jusqu'à ce
qu'on le remette à `false`.

```bash
kubectl patch cronjob releve -n essai-lots -p '{"spec":{"suspend":true}}'; kubectl get cronjob releve -n essai-lots
```

```text
cronjob.batch/releve patched
NAME     SCHEDULE       TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
releve   */10 * * * *   <none>     True      0        <none>          3s
```

`SUSPEND True` : le CronJob est en pause.

## 🧹 Nettoyage

Supprimez le namespace d'essai et le fichier de travail :

```bash
kubectl delete namespace essai-lots; rm -f ~/traitement.yaml
```

```text
namespace "essai-lots" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-job-cronjob
dsoxlab check ckad-job-cronjob
```

```text
╭─── Résultat : ckad-job-cronjob ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un autre Job, avec ses propres nombres de réussites
et de Pods à la fois, et un autre CronJob, à lancer aussi à la main.

```bash
dsoxlab run ckad-job-cronjob
dsoxlab challenge ckad-job-cronjob
```
