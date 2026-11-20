# Preview with diff, wait with wait

Before applying a change, you want to know what it will modify. After applying
it, you want to know when it is really over. `kubectl diff` answers the first
question, `kubectl rollout status` and `kubectl wait` the second one. The
lesson presents them and puts together a deployment script. This course starts
from what goes wrong: a stuck rollout that you undo, a folder that no longer
says what the cluster runs, a Job that fails without the wait seeing it, Jobs
to wait for in a folder, and an `apply` that stops halfway.

You work in a scratch namespace, `essai-attente`, with an `accueil`
Deployment and two scratch Jobs. A **Job** starts a Pod that does a task, then
stops: the lesson on Jobs details them later in the training. The challenge
will ask you for a complete deployment script, on another application: you
will write it on your own, at the end.

Related page: [kubectl wait and diff](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-wait-diff/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-verifier-et-attendre
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab`
is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.0.

Prepare the scratch namespace and a folder holding the `accueil` Deployment: 3
nginx Pods in version 1.30.5, with a readiness probe. Apply it and wait until
it is ready:

```bash
kubectl create namespace essai-attente; mkdir -p ~/essai-attente
cat > ~/essai-attente/accueil.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accueil
  namespace: essai-attente
spec:
  replicas: 3
  selector:
    matchLabels:
      app: accueil
  template:
    metadata:
      labels:
        app: accueil
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
YAML
kubectl apply -f ~/essai-attente/accueil.yaml && kubectl rollout status deployment/accueil -n essai-attente --timeout=180s | tail -1
```

```text
namespace/essai-attente created
deployment.apps/accueil created
deployment "accueil" successfully rolled out
```

## 📚 Exercise 1: reminder, the codes of diff and set -e

The lesson details the three exit codes of `kubectl diff`. Go over them in one
go. Change the image of the file to a version that **does not exist**,
`nginx:1.30.6-introuvable`, then compare the folder, and finally a missing
file. `grep` only keeps the changed lines, and `${PIPESTATUS[0]}` gives the
code of `kubectl diff`, not the one of `grep`:

```bash
kubectl diff -f ~/essai-attente/; echo "code $?"
sed -i 's/image: nginx:1.30.5@sha256:[0-9a-f]*/image: nginx:1.30.6-introuvable/' ~/essai-attente/accueil.yaml; kubectl diff -f ~/essai-attente/ | grep -E '^[-+] '; echo "code ${PIPESTATUS[0]}"
kubectl diff -f ~/essai-attente/introuvable.yaml; echo "code $?"
```

```text
code 0
-  generation: 1
+  generation: 2
-      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
+      - image: nginx:1.30.6-introuvable
code 1
error: the path "/home/ansible/essai-attente/introuvable.yaml" does not exist
code 2
```

0: no difference. 1: differences, which is not an error. 2: kubectl could not
compare. Under `set -e`, which stops a script at the first failing command,
code 1 stops everything at the very moment you should apply. `|| code=$?`
keeps the code without stopping the script:

```bash
bash -c 'set -e; kubectl diff -f ~/essai-attente/ > /dev/null; echo "je continue"'; echo "code $?"
bash -c 'set -e; code=0; kubectl diff -f ~/essai-attente/ > /dev/null || code=$?; echo "diff a rendu $code"'
```

```text
code 1
diff a rendu 1
```

## 📚 Exercise 2: a stuck rollout, then undone

Apply the file, which now asks for the missing image, and wait for the end of
the rollout with a 30-second timeout:

```bash
kubectl apply -f ~/essai-attente/accueil.yaml; kubectl rollout status deployment/accueil -n essai-attente --timeout=30s; echo "code $?"
kubectl get pods -n essai-attente -l app=accueil
```

```text
deployment.apps/accueil configured
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
error: timed out waiting for the condition
code 1
NAME                      READY   STATUS             RESTARTS   AGE
accueil-5c6db657b-2kznd   1/1     Running            0          42s
accueil-5c6db657b-5ksz9   1/1     Running            0          42s
accueil-5c6db657b-qjnwb   1/1     Running            0          42s
accueil-db88c9bcd-6s4vp   0/1     ImagePullBackOff   0          31s
```

`rollout status` gives control back at the end of the timeout, with code 1:
the rollout did not finish. The new Pod cannot find its image
(`ImagePullBackOff`), and the three old ones keep serving. In a script, this
code 1 is what must stop the rest. Go back to the previous version with
`rollout undo`:

```bash
kubectl rollout undo deployment/accueil -n essai-attente; kubectl rollout status deployment/accueil -n essai-attente --timeout=120s | tail -1
kubectl get deployment accueil -n essai-attente -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
Warning: resource deployments/accueil was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/accueil rolled back
deployment "accueil" successfully rolled out
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

The cluster is back on 1.30.5. The warning says it: `undo` does not touch the
file. Compare the folder with the cluster:

```bash
kubectl diff -f ~/essai-attente/ | grep -E '^[-+] .*image'; echo "code ${PIPESTATUS[0]}"
```

```text
-      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
+      - image: nginx:1.30.6-introuvable
code 1
```

`diff` returns 1 again: the folder still asks for the missing image, and the
next `apply` would start the same failure again. After an `undo`, fix the file
as well:

```bash
sed -i 's/image: nginx:1.30.6-introuvable/image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb/' ~/essai-attente/accueil.yaml; kubectl diff -f ~/essai-attente/ > /dev/null; echo "code $?"
```

```text
code 0
```

## 📚 Exercise 3: a Job that fails

Write two Jobs in a `taches` subfolder: `vider-cache` works for 6 seconds then
succeeds, `tache-ratee` fails right away (`exit 3`). `backoffLimit: 0` forbids
restarting a failed Pod:

```bash
mkdir -p ~/essai-attente/taches
cat > ~/essai-attente/taches/vider-cache.yaml <<'YAML'
apiVersion: batch/v1
kind: Job
metadata:
  name: vider-cache
  namespace: essai-attente
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: vider
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo cache en cours de vidage; sleep 6; echo cache vide"]
YAML
cat > ~/essai-attente/taches/tache-ratee.yaml <<'YAML'
apiVersion: batch/v1
kind: Job
metadata:
  name: tache-ratee
  namespace: essai-attente
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: tache
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo echec volontaire; exit 3"]
YAML
kubectl apply -f ~/essai-attente/taches/
```

```text
job.batch/tache-ratee created
job.batch/vider-cache created
```

Wait for the success of `tache-ratee`, then for its failure. `time` measures
how long each command lasts (`real` line):

```bash
time kubectl wait --for=condition=Complete job/tache-ratee -n essai-attente --timeout=15s
time kubectl wait --for=condition=Failed job/tache-ratee -n essai-attente --timeout=15s
```

```text
error: timed out waiting for the condition on jobs/tache-ratee

real	0m15.051s
user	0m0.026s
sys	0m0.017s
job.batch/tache-ratee condition met

real	0m0.159s
user	0m0.031s
sys	0m0.005s
```

`Complete` waited the 15 seconds for nothing: a failed Job never meets it.
`Failed` answers right away. With a 300-second timeout in a pipeline, waiting
for success alone means losing five minutes before you know.

## 📚 Exercise 4: wait for all the Jobs of a folder

A deployment script does not know the objects of a folder in advance:
`kubectl get -f` lists them. Try with `-o name`, then wait for the first Job
found that way:

```bash
kubectl get -f ~/essai-attente/taches/ -o name
kubectl wait --for=condition=Complete job/vider-cache --timeout=0
```

```text
job.batch/tache-ratee
job.batch/vider-cache
Error from server (NotFound): jobs.batch "vider-cache" not found
```

The Job does exist. `-o name` does not give the namespace, and `wait` looked
in the one of the context, `default`. Ask for the namespace as well, with
`custom-columns` and without a line of titles. Try on the folder, then on a
single file:

```bash
kubectl get -f ~/essai-attente/taches/ -o custom-columns=KIND:.kind,NS:.metadata.namespace,NOM:.metadata.name --no-headers
kubectl get -f ~/essai-attente/taches/vider-cache.yaml -o custom-columns=KIND:.kind,NS:.metadata.namespace,NOM:.metadata.name --no-headers
```

```text
Job   essai-attente   tache-ratee
Job   essai-attente   vider-cache
Job   essai-attente   vider-cache
```

One line per object, in both cases. With a single object, `kubectl get` does
not return a list: a JSONPath that goes through `.items` would then find
nothing, while `custom-columns` always works.

Write a script that reads these lines and, for each Job, queries `Complete`
then `Failed` in turn with `--timeout=0` (a single check, without waiting), in
a loop bounded to 60 seconds. It exits with an error at the first Job that
fails:

```bash
cat > ~/essai-attente/attendre-jobs.sh <<'EOF'
#!/usr/bin/env bash
# Usage : ./attendre-jobs.sh <dossier> : attend chaque Job du dossier, et sort
# en erreur au premier qui échoue.
set -euo pipefail
while read -r kind ns nom; do
  [ "$kind" = Job ] || continue
  fin=$((SECONDS + 60)); etat=2
  while [ "$SECONDS" -lt "$fin" ]; do
    if kubectl wait --for=condition=Complete "job/$nom" -n "$ns" --timeout=0 >/dev/null 2>&1; then etat=0; break; fi
    if kubectl wait --for=condition=Failed "job/$nom" -n "$ns" --timeout=0 >/dev/null 2>&1; then etat=1; break; fi
    sleep 2
  done
  echo "job/$nom : code $etat"
  [ "$etat" -eq 0 ] || exit 1
done < <(kubectl get -f "$1" -o custom-columns=KIND:.kind,NS:.metadata.namespace,NOM:.metadata.name --no-headers)
echo "Tous les Jobs sont terminés."
EOF
chmod +x ~/essai-attente/attendre-jobs.sh
time ~/essai-attente/attendre-jobs.sh ~/essai-attente/taches/; echo "code $?"
```

```text
job/tache-ratee : code 1

real	0m0.118s
user	0m0.078s
sys	0m0.029s
code 1
```

The script sees the failure of `tache-ratee` on the first round, and exits with
an error right away. `[ "$kind" = Job ] || continue` skips the objects that
are not Jobs, and `< <(...)` feeds the loop with the output of `kubectl get`.
Remove the failed Job from the folder, and run it again:

```bash
rm ~/essai-attente/taches/tache-ratee.yaml; ~/essai-attente/attendre-jobs.sh ~/essai-attente/taches/; echo "code $?"
```

```text
job/vider-cache : code 0
Tous les Jobs sont terminés.
code 0
```

## 📚 Exercise 5: a folder where one object is refused

Prepare a `lot` folder with two files: a correct ConfigMap, and a `casse`
Deployment whose selector (`app: casse`) does not match the labels of its Pods
(`app: autre-chose`). Compare it with the cluster:

```bash
mkdir -p ~/essai-attente/lot
cat > ~/essai-attente/lot/a-reglages.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: reglages-accueil
  namespace: essai-attente
data:
  THEME: clair
YAML
cat > ~/essai-attente/lot/b-casse.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: casse
  namespace: essai-attente
spec:
  replicas: 1
  selector:
    matchLabels:
      app: casse
  template:
    metadata:
      labels:
        app: autre-chose
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
kubectl diff -f ~/essai-attente/lot/ > /dev/null; echo "diff : code $?"
```

```text
The Deployment "casse" is invalid: spec.template.metadata.labels: Invalid value: {"app":"autre-chose"}: `selector` does not match template `labels`
diff : code 2
```

`diff` cannot compare an object the server refuses: code 2. See what `apply`
does on the same folder:

```bash
kubectl apply -f ~/essai-attente/lot/; echo "apply : code $?"
kubectl get configmap reglages-accueil -n essai-attente; kubectl get deployment casse -n essai-attente
```

```text
configmap/reglages-accueil created
The Deployment "casse" is invalid: spec.template.metadata.labels: Invalid value: {"app":"autre-chose"}: `selector` does not match template `labels`
apply : code 1
NAME               DATA   AGE
reglages-accueil   1      0s
Error from server (NotFound): deployments.apps "casse" not found
```

`apply` exits with an error, but it **still** created the ConfigMap. The
cluster is now half changed. That is why a deployment script compares first,
and stops without applying anything when `diff` returns 2 or more.

## 🧹 Clean up

Delete the scratch namespace and the work folder:

```bash
kubectl delete namespace essai-attente; rm -rf ~/essai-attente
```

```text
namespace "essai-attente" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-verifier-et-attendre
dsoxlab check k8s-verifier-et-attendre
```

```text
╭─ Result: k8s-verifier-et-attendre ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests   │
╰────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: move another application to version 2, wait
for the real end of the rollout and of a Job, record the revision reached,
and write a deployment script that knows when to stop, including when a Job
fails.

```bash
dsoxlab run k8s-verifier-et-attendre
dsoxlab challenge k8s-verifier-et-attendre
```
