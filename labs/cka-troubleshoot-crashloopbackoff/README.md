# Get a Deployment out of CrashLoopBackOff

The lesson shows the `CrashLoopBackOff` state: a container that starts,
crashes, and that the kubelet restarts endlessly. This course has you
investigate such a container, and adds cases the lesson does not show: the
logs of the previous run, the delay between two restarts that grows, and a
container that crashes too fast to get into, inspected through a copy whose
command is changed.

You work in a scratch namespace, `essai-boucle`, with a `fichier-absent`
("missing-file") Pod that cannot find its configuration file. The challenge
is about another application: you will do it on your own, at the end.

Related page: [CrashLoopBackOff](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/crashloopbackoff/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-crashloopbackoff
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace, a ConfigMap carrying a `service.ini` key, and a Pod
that mounts this ConfigMap on `/conf` and reads `/conf/app.ini`. If it does
not find it, it exits with code 4. The command waits one minute:

```bash
kubectl create namespace essai-boucle; kubectl create configmap reglages -n essai-boucle --from-literal=service.ini='port=9000'; cat <<YAML | kubectl apply -n essai-boucle -f -
apiVersion: v1
kind: Pod
metadata:
  name: fichier-absent
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo lecture de /conf/app.ini; cat /conf/app.ini || exit 4; sleep 3600"]
      volumeMounts:
        - {name: conf, mountPath: /conf}
  volumes:
    - name: conf
      configMap: {name: reglages}
YAML
sleep 60; kubectl get pod fichier-absent -n essai-boucle
```

```text
namespace/essai-boucle created
configmap/reglages created
pod/fichier-absent created
NAME             READY   STATUS   RESTARTS      AGE
fichier-absent   0/1     Error    3 (47s ago)   60s
```

Three restarts in one minute: the Pod is looping.

## 📜 Exercise 1: read the previous run

Wait for the Pod to be in `CrashLoopBackOff`, between two restarts, then read
its logs, and those of the previous run (`--previous`):

```bash
until [ "$(kubectl get pod fichier-absent -n essai-boucle -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}')" = CrashLoopBackOff ]; do sleep 2; done; kubectl logs fichier-absent -n essai-boucle; echo '--- précédente :'; kubectl logs fichier-absent -n essai-boucle --previous
```

```text
lecture de /conf/app.ini
cat: can't open '/conf/app.ini': No such file or directory
--- précédente :
lecture de /conf/app.ini
cat: can't open '/conf/app.ini': No such file or directory
```

Both say the same thing: the file does not exist. `--previous` is valuable
when the current container has already restarted and has written nothing
yet: it gives the end of the run that crashed. Also read that end's code and
reason:

```bash
kubectl get pod fichier-absent -n essai-boucle -o jsonpath='code={.status.containerStatuses[0].lastState.terminated.exitCode} raison={.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text
code=4 raison=Error
```

Code 4 is the one the program chose (`exit 4`). A code specific to the
program points to the application. A code 137 would point to a forced stop,
often for lack of memory.

## ⏱️ Exercise 2: the delay between two restarts grows

Count the starts, and read the Pod's waiting message (`relances` means
"restarts", `attente` "waiting"):

```bash
until [ "$(kubectl get pod fichier-absent -n essai-boucle -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}')" = CrashLoopBackOff ]; do sleep 2; done; kubectl get events -n essai-boucle --field-selector involvedObject.name=fichier-absent,reason=Started -o custom-columns=NOMBRE:.count,PREMIER:.firstTimestamp,DERNIER:.lastTimestamp; kubectl get pod fichier-absent -n essai-boucle -o jsonpath='relances={.status.containerStatuses[0].restartCount} attente={.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```text
NOMBRE   PREMIER                DERNIER
5        2026-11-21T04:51:45Z   2026-11-21T04:53:08Z
relances=4 attente=back-off 1m20s restarting failed container=app pod=fichier-absent_essai-boucle(3c04a7e7-3254-419c-8ebc-c0f47217ba2c)
```

Five starts, and the kubelet now waits 1 minute 20 before the next one. It
doubles the delay at each failure (10 s, 20 s, 40 s…), up to 5 minutes. A Pod
that has been looping for a long time therefore only restarts every 5
minutes: a fix can look ineffective if you do not wait for the next restart.

## 🔍 Exercise 3: get into a copy that does not crash

Try to get into the container to see what `/conf` holds:

```bash
kubectl exec fichier-absent -n essai-boucle -- ls /conf; echo "exec : code $?"
```

```text
error: unable to upgrade connection: container not found ("app")
exec : code 1
```

Impossible: between two restarts, the container does not exist.
`kubectl debug --copy-to` creates a copy of the Pod, with another command,
here a simple `sleep` that does not crash. Get into the copy:

```bash
kubectl debug fichier-absent -n essai-boucle --copy-to=fichier-absent-copie --container=app -- sleep 3600 >/dev/null; kubectl wait --for=condition=Ready pod/fichier-absent-copie -n essai-boucle --timeout=60s; kubectl exec fichier-absent-copie -n essai-boucle -- ls -l /conf/
```

```text
pod/fichier-absent-copie condition met
total 0
lrwxrwxrwx    1 root     root            18 Nov 21 04:54 service.ini -> ..data/service.ini
```

`/conf` holds `service.ini`, not `app.ini`. Check the ConfigMap:

```bash
kubectl get configmap reglages -n essai-boucle -o jsonpath='{.data}{"\n"}'
```

```text
{"service.ini":"port=9000"}
```

The cause is found: the ConfigMap's key does not have the name the
application looks for. The copy was used to look, without touching the
original Pod, which still crashes.

## 🧹 Clean-up

Delete the scratch namespace. The copy goes with it:

```bash
kubectl delete namespace essai-boucle
```

```text
namespace "essai-boucle" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-crashloopbackoff
dsoxlab check cka-troubleshoot-crashloopbackoff
```

```text
╭─ Result: cka-troubleshoot-crashloopbackoff ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests            │
╰─────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a looping Deployment, whose cause you must
find and fix on the Deployment itself.

```bash
dsoxlab run cka-troubleshoot-crashloopbackoff
dsoxlab challenge cka-troubleshoot-crashloopbackoff
```
