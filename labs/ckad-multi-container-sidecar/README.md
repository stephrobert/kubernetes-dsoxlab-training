# A native sidecar that follows the application's logs

A **sidecar** is a helper container, placed in the same Pod as an application
to help it: read its files, relay its traffic, ship its logs elsewhere.
Kubernetes offers a precise way to declare it, the **native sidecar**. In this
course, you see an application that `kubectl logs` does not show, you add a
reader to it as a second container, then as a native sidecar, and you see on a
Job what sets them apart.

You work in a scratch namespace, `essai-sidecar`, with a counter (`compteur`)
that writes to a file and a reader (`lecteur`) that relays it. The challenge
will ask you for the same thing on another application, in another namespace:
you will do it on your own, at the end.

Related page: [Init containers and sidecars](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/init-containers-and-sidecars/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-multi-container-sidecar
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: an application that writes to a file

Create the scratch namespace and a `compteur-seul` Pod. Its container writes a
line every 2 seconds ("passage" means "pass") into `/donnees/journal.txt`, on
an `emptyDir` volume (an empty directory, created with the Pod):

```bash
kubectl create namespace essai-sidecar
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur-seul
spec:
  containers:
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "i=0; while true; do i=$((i+1)); echo passage $i >> /donnees/journal.txt; sleep 2; done"]
      volumeMounts:
        - name: donnees
          mountPath: /donnees
  volumes:
    - name: donnees
      emptyDir: {}
YAML
```

```text
namespace/essai-sidecar created
pod/compteur-seul created
```

Wait until it runs, then read its logs (`echo` marks the end of the output;
"fin des logs" means "end of logs"):

```bash
kubectl wait --for=condition=Ready pod/compteur-seul -n essai-sidecar --timeout=120s; sleep 6; kubectl logs compteur-seul -n essai-sidecar; echo '(fin des logs)'
```

```text
pod/compteur-seul condition met
(fin des logs)
```

Nothing. `kubectl logs` only shows what a container writes to its **standard
output**. This counter writes to a file, which does fill up:

```bash
kubectl exec compteur-seul -n essai-sidecar -- tail -3 /donnees/journal.txt
```

```text
passage 2
passage 3
passage 4
```

## 📚 Exercise 2: a second container that reads the file

Add a second container to the Pod, `lecteur`, which follows the file with
`tail -F` and copies it to its own standard output. Two containers of the same
Pod share no file by default: the `donnees` volume is therefore mounted in
both. The path can differ: `/donnees` for the counter, `/lecture` for the
reader. `touch` creates the file if it does not exist yet:

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur-classique
spec:
  containers:
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "i=0; while true; do i=$((i+1)); echo passage $i >> /donnees/journal.txt; sleep 2; done"]
      volumeMounts:
        - name: donnees
          mountPath: /donnees
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
      volumeMounts:
        - name: donnees
          mountPath: /lecture
  volumes:
    - name: donnees
      emptyDir: {}
YAML
```

```text
pod/compteur-classique created
```

`-c lecteur` picks the container whose logs you read:

```bash
kubectl wait --for=condition=Ready pod/compteur-classique -n essai-sidecar --timeout=120s; sleep 6; kubectl get pod compteur-classique -n essai-sidecar; kubectl logs compteur-classique -n essai-sidecar -c lecteur | tail -3
```

```text
pod/compteur-classique condition met
NAME                 READY   STATUS    RESTARTS   AGE
compteur-classique   2/2     Running   0          7s
passage 2
passage 3
passage 4
```

The counter's lines show up in the reader's logs. For a Pod that runs forever,
this form is enough. Exercise 4 shows where it gets stuck.

## 📚 Exercise 3: the same reader as a native sidecar

A **native sidecar** is declared under `initContainers`, with
`restartPolicy: Always`. Without that line, it would be an ordinary init
container, which must finish before the application starts. With it,
Kubernetes starts it before the application and keeps it running alongside:

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur-natif
spec:
  initContainers:
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      restartPolicy: Always
      command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
      volumeMounts:
        - name: donnees
          mountPath: /lecture
  containers:
    - name: compteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "i=0; while true; do i=$((i+1)); echo passage $i >> /donnees/journal.txt; sleep 2; done"]
      volumeMounts:
        - name: donnees
          mountPath: /donnees
  volumes:
    - name: donnees
      emptyDir: {}
YAML
```

```text
pod/compteur-natif created
```

```bash
kubectl wait --for=condition=Ready pod/compteur-natif -n essai-sidecar --timeout=120s; sleep 6; kubectl get pod compteur-natif -n essai-sidecar; kubectl logs compteur-natif -n essai-sidecar -c lecteur | tail -3
```

```text
pod/compteur-natif condition met
NAME             READY   STATUS    RESTARTS   AGE
compteur-natif   2/2     Running   0          7s
passage 1
passage 2
passage 3
```

Same result, `2/2` included: a native sidecar counts among the ready
containers. Check where each one is declared:

```bash
kubectl get pod compteur-natif -n essai-sidecar -o jsonpath='init : {.spec.initContainers[0].name} restartPolicy={.spec.initContainers[0].restartPolicy}{"\n"}principal : {.spec.containers[0].name}{"\n"}'
```

```text
init : lecteur restartPolicy=Always
principal : compteur
```

## 📚 Exercise 4: a Job with a classic sidecar

The difference shows on a **Job**, a Pod that does a task then stops. Start a
`rapport-classique` Job ("rapport" means "report"): its `rapport` container
writes three lines in 3 seconds then exits, and the reader is a second
ordinary container, as in exercise 2:

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: rapport-classique
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: rapport
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "for i in 1 2 3; do echo ligne $i >> /donnees/journal.txt; sleep 1; done; echo rapport termine"]
          volumeMounts:
            - name: donnees
              mountPath: /donnees
        - name: lecteur
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
          volumeMounts:
            - name: donnees
              mountPath: /lecture
      volumes:
        - name: donnees
          emptyDir: {}
YAML
```

```text
job.batch/rapport-classique created
```

25 seconds later:

```bash
sleep 25; kubectl get job rapport-classique -n essai-sidecar; kubectl get pods -n essai-sidecar -l job-name=rapport-classique
```

```text
NAME                STATUS    COMPLETIONS   DURATION   AGE
rapport-classique   Running   0/1           25s        25s
NAME                      READY   STATUS     RESTARTS   AGE
rapport-classique-mf8br   1/2     NotReady   0          25s
```

The report finished long ago, but the Job is still running (`0/1`): the reader
never stops. A Job is only finished when **all** its ordinary containers are.
This Job will never finish.

## 📚 Exercise 5: the same Job with a native sidecar

Same Job, but the reader becomes a native sidecar:

```bash
cat <<'YAML' | kubectl apply -n essai-sidecar -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: rapport-natif
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      initContainers:
        - name: lecteur
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          restartPolicy: Always
          command: ["sh", "-c", "touch /lecture/journal.txt; tail -n +1 -F /lecture/journal.txt"]
          volumeMounts:
            - name: donnees
              mountPath: /lecture
      containers:
        - name: rapport
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "for i in 1 2 3; do echo ligne $i >> /donnees/journal.txt; sleep 1; done; echo rapport termine"]
          volumeMounts:
            - name: donnees
              mountPath: /donnees
      volumes:
        - name: donnees
          emptyDir: {}
YAML
```

```text
job.batch/rapport-natif created
```

```bash
kubectl wait --for=condition=complete job/rapport-natif -n essai-sidecar --timeout=120s; kubectl get job rapport-natif -n essai-sidecar; kubectl get pods -n essai-sidecar -l job-name=rapport-natif
kubectl logs job/rapport-natif -n essai-sidecar -c lecteur
```

```text
job.batch/rapport-natif condition met
NAME            STATUS     COMPLETIONS   DURATION   AGE
rapport-natif   Complete   1/1           37s        37s
NAME                  READY   STATUS      RESTARTS   AGE
rapport-natif-drwr6   0/2     Completed   0          37s
ligne 1
ligne 2
ligne 3
```

The Job finishes (`Complete`) and the reader did relay the three lines. When
the main container has finished, Kubernetes stops the native sidecar itself.
But why 37 seconds for 3 seconds of work? Look at how each container stopped:

```bash
kubectl get pods -n essai-sidecar -l job-name=rapport-natif -o jsonpath='{range .items[0].status.initContainerStatuses[*]}{.name} {.state.terminated.reason} {.state.terminated.exitCode}{"\n"}{end}{range .items[0].status.containerStatuses[*]}{.name} {.state.terminated.reason} {.state.terminated.exitCode}{"\n"}{end}'
```

```text
lecteur Error 137
rapport Completed 0
```

The report ended normally (code 0). The reader has code 137: it was **killed
by force**. Kubernetes first asked it to stop, but `tail`, started by
`sh -c`, did not react. So Kubernetes waited for the allowed delay, 30 seconds
by default, before killing it. A sidecar that stops cleanly when asked does
not keep its Job waiting.

## 🧹 Clean up

Delete the scratch namespace, with its Pods and Jobs:

```bash
kubectl delete namespace essai-sidecar
```

```text
namespace "essai-sidecar" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-multi-container-sidecar
dsoxlab check ckad-multi-container-sidecar
```

```text
╭─ Result: ckad-multi-container-sidecar ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests       │
╰────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another application that writes its logs to
a file, and a native sidecar that relays them.

```bash
dsoxlab run ckad-multi-container-sidecar
dsoxlab challenge ckad-multi-container-sidecar
```
