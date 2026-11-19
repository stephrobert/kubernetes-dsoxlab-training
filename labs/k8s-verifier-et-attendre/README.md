# Preview with diff, wait with wait

Before applying a change, you want to know what it will modify. After applying
it, you want to know when it is really finished. `kubectl diff` answers the
first question, `kubectl rollout status` and `kubectl wait` the second. In
this course, you measure the exit codes of `kubectl diff`, you see the trap
they set for a script, you tell an available rollout from a finished one, you
wait for the end of a Job that succeeds then of a Job that fails, and you see
what `apply` does when an object in the folder is refused.

You work in a scratch namespace, `essai-attente`, with an `accueil` Deployment
and two trial Jobs. The challenge will ask you for the same thing on another
application: you will do it on your own, at the end.

Related page: [kubectl wait and diff](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/outils/kubectl-wait-diff/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-verifier-et-attendre
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab` is
running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes 1.37.

Prepare the scratch namespace and a folder that holds the `accueil`
Deployment: 3 nginx Pods at version 1.30.5, with a readiness probe. Apply it
and wait until it is ready:

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

## 📚 Exercise 1: the three codes of kubectl diff

`kubectl diff` compares a file or a folder with what runs in the cluster. Its
**exit code** (which the shell stores in `$?`) tells what it found. Compare the
folder as it is:

```bash
kubectl diff -f ~/essai-attente/; echo "code $?"
```

```text
code 0
```

No difference: nothing is shown, and the code is 0. Now set the image of the
file to version 1.30.6, then compare again. `grep` keeps only the changed
lines, and `${PIPESTATUS[0]}` gives the code of `kubectl diff` (not the one of
`grep`):

```bash
sed -i 's/nginx:1.30.5@sha256:[0-9a-f]*/nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703/' ~/essai-attente/accueil.yaml; kubectl diff -f ~/essai-attente/ | grep -E '^[-+] '; echo "code ${PIPESTATUS[0]}"
```

```text
-  generation: 1
+  generation: 2
-      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
+      - image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
code 1
```

The `-` shows what runs, the `+` what `apply` would give. The code is 1.
Finally, ask for an impossible comparison, on a file that does not exist:

```bash
kubectl diff -f ~/essai-attente/introuvable.yaml; echo "code $?"
```

```text
error: the path "/home/ansible/essai-attente/introuvable.yaml" does not exist
code 2
```

The three cases:

- **0**: no difference;
- **1**: differences, which is **not** an error;
- **2** (or more): kubectl could not compare, this is a real error.

## 📚 Exercise 2: diff under set -e

A script often starts with `set -e`: it stops as soon as a command exits with a
code other than 0. See what happens with `kubectl diff`, while the folder does
hold differences ("je continue" means "I carry on"):

```bash
bash -c 'set -e; kubectl diff -f ~/essai-attente/ > /dev/null; echo "je continue"'; echo "code $?"
```

```text
code 1
```

The script stops before `je continue`, at the very moment it should apply. For
`set -e`, the code 1 of `diff` is a failure. The fix: keep the code in a
variable. `|| code=$?` runs only if `diff` exits with an error, and `set -e`
does not stop on a command followed by `||` ("diff a rendu" means "diff
returned"):

```bash
bash -c 'set -e; code=0; kubectl diff -f ~/essai-attente/ > /dev/null || code=$?; echo "diff a rendu $code"'
```

```text
diff a rendu 1
```

The script carries on and knows the code: 0, nothing to do; 1, apply; 2 or
more, stop.

## 📚 Exercise 3: available is not finished

Apply the image change, then wait until the Deployment is **Available**, and
look at its Pods right away. The columns give the name of the Pod, whether it
is ready (`PRET`), whether it is stopping (`ARRET`), and the beginning of its
image:

```bash
kubectl apply -f ~/essai-attente/accueil.yaml && kubectl wait --for=condition=Available deployment/accueil -n essai-attente --timeout=60s && kubectl get pods -n essai-attente -l app=accueil -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,ARRET:.metadata.deletionTimestamp,IMAGE:.spec.containers[0].image' | cut -c1-82
```

```text
deployment.apps/accueil configured
deployment.apps/accueil condition met
POD                        PRET    ARRET    IMAGE
accueil-5c6db657b-hjpjh    true    <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1
accueil-5c6db657b-qr7q2    true    <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1
accueil-5c6db657b-vpwpn    true    <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1
accueil-5cbc7d7b69-mnpwg   false   <none>   nginx:1.30.6@sha256:42c68eab6f7e226117
```

`wait` returned right away. Yet the three 1.30.5 Pods still serve, and the only
1.30.6 Pod is not ready. **Available** means "enough ready Pods to serve", not
"update finished".

`kubectl rollout status`, on the other hand, waits until all the Pods are
replaced:

```bash
kubectl rollout status deployment/accueil -n essai-attente --timeout=180s
```

```text
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "accueil" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "accueil" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "accueil" rollout to finish: 1 old replicas are pending termination...
deployment "accueil" successfully rolled out
```

Look at the Pods again:

```bash
kubectl get pods -n essai-attente -l app=accueil -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,ARRET:.metadata.deletionTimestamp,IMAGE:.spec.containers[0].image' | cut -c1-82
```

```text
POD                        PRET   ARRET                  IMAGE
accueil-5c6db657b-vpwpn    true   2026-11-19T19:31:01Z   nginx:1.30.5@sha256:9bf97
accueil-5cbc7d7b69-844tt   true   <none>                 nginx:1.30.6@sha256:42c68
accueil-5cbc7d7b69-mnpwg   true   <none>                 nginx:1.30.6@sha256:42c68
accueil-5cbc7d7b69-v8nm9   true   <none>                 nginx:1.30.6@sha256:42c68
```

The three 1.30.6 Pods are ready. The last 1.30.5 Pod has a date in `ARRET`: it
is stopping, and is already no longer part of the Deployment. The folder and
the cluster now say the same thing:

```bash
kubectl diff -f ~/essai-attente/; echo "code $?"
```

```text
code 0
```

## 📚 Exercise 4: wait for the end of a Job

A **Job** starts a Pod that does a task, then stops. Start a Job that works for
6 seconds:

```bash
cat <<'YAML' | kubectl apply -f -
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
```

```text
job.batch/vider-cache created
```

`kubectl wait --for=condition=complete` waits until the Job has finished
successfully. `time` measures how long the command took (`real` line):

```bash
time kubectl wait --for=condition=complete job/vider-cache -n essai-attente --timeout=60s
kubectl logs job/vider-cache -n essai-attente
```

```text
job.batch/vider-cache condition met

real	0m8.812s
user	0m0.030s
sys	0m0.008s
cache en cours de vidage
cache vide
```

`wait` returned after about 9 seconds, when the Job finished. Its logs ("cache
being emptied", "cache empty") confirm it.

## 📚 Exercise 5: a Job that fails

Start a Job that fails at once (`exit 3`). `backoffLimit: 0` forbids starting
it again:

```bash
cat <<'YAML' | kubectl apply -f -
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
```

```text
job.batch/tache-ratee created
```

Wait for it to succeed, as for the previous Job:

```bash
time kubectl wait --for=condition=complete job/tache-ratee -n essai-attente --timeout=20s
```

```text
error: timed out waiting for the condition on jobs/tache-ratee

real	0m20.037s
user	0m0.026s
sys	0m0.009s
```

`wait` waited the 20 seconds of `--timeout` for nothing: a failed Job will
never be `complete`. Without `--timeout`, it would have waited 30 seconds, the
default value, and much longer with a bigger `--timeout`. Wait for the
**failed** condition instead:

```bash
time kubectl wait --for=condition=failed job/tache-ratee -n essai-attente --timeout=20s
kubectl get job tache-ratee -n essai-attente
```

```text
job.batch/tache-ratee condition met

real	0m0.137s
user	0m0.025s
sys	0m0.011s
NAME          STATUS   COMPLETIONS   DURATION   AGE
tache-ratee   Failed   0/1           20s        20s
```

Immediate answer: the Job has failed. To avoid being stuck, always wait with a
`--timeout`, and also watch the `failed` condition.

## 📚 Exercise 6: a folder where one object is refused

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
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests   │
╰────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: move another application to version 2, wait
for the real end of the rollout and of a Job, record the codes of `kubectl
diff`, and write a small deployment script that knows when to stop.

```bash
dsoxlab run k8s-verifier-et-attendre
dsoxlab challenge k8s-verifier-et-attendre
```
