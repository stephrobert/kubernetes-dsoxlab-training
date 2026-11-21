# Three Pods in CrashLoopBackOff, three causes

The lesson shows how to find why a container restarts in a loop. This course
adds causes the lesson does not show: a liveness probe that kills an
application slow to start, a program that succeeds and loops anyway, a
`command` that replaces the program planned by the image, and the
termination message a container can leave to explain why it stopped.

You work in a scratch namespace, `essai-relance` ("test-restart"), with
scratch Pods. The challenge is about three other Pods: you will do it on your
own, at the end.

Related page: [CrashLoopBackOff](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/crashloopbackoff/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-troubleshoot-crashloop
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🐢 Exercise 1: a liveness probe that kills a slow application

Create an nginx Pod that waits 25 seconds before starting, with a liveness
probe that declares it dead after 2 failures 5 seconds apart. The command
waits 50 seconds, then reads the `Killing` event:

```bash
kubectl create namespace essai-relance; cat <<YAML | kubectl apply -n essai-relance -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent
spec:
  containers:
    - name: lent
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      command: ["sh", "-c", "sleep 25; exec nginx -g 'daemon off;'"]
      livenessProbe:
        httpGet: {path: /, port: 80}
        periodSeconds: 5
        failureThreshold: 2
YAML
sleep 50; kubectl get pod lent -n essai-relance; kubectl get events -n essai-relance --field-selector involvedObject.name=lent,reason=Killing -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
namespace/essai-relance created
pod/lent created
NAME   READY   STATUS    RESTARTS      AGE
lent   1/1     Running   1 (10s ago)   50s
Container lent failed liveness probe, will be restarted
```

One restart: the probe failed during the 25 seconds of startup, and the
kubelet killed the container. An over-eager liveness probe makes a healthy
but slow application restart in a loop. Recreate the Pod with a startup probe
(`startupProbe`) that gives it one minute (12 attempts of 5 seconds):

```bash
kubectl delete pod lent -n essai-relance; cat <<YAML | kubectl apply -n essai-relance -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent
spec:
  containers:
    - name: lent
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      command: ["sh", "-c", "sleep 25; exec nginx -g 'daemon off;'"]
      startupProbe:
        httpGet: {path: /, port: 80}
        periodSeconds: 5
        failureThreshold: 12
      livenessProbe:
        httpGet: {path: /, port: 80}
        periodSeconds: 5
        failureThreshold: 2
YAML
sleep 50; kubectl get pod lent -n essai-relance
```

```text
pod "lent" deleted from essai-relance namespace
pod/lent created
NAME   READY   STATUS    RESTARTS   AGE
lent   1/1     Running   0          50s
```

No restart. As long as the startup probe has not succeeded, the liveness probe
does not run.

## ✅ Exercise 2: a program that succeeds, and loops anyway

Start a Pod whose program does its job and exits with code 0 (`dernier code`
means "last code"):

```bash
kubectl run sage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-relance -- sh -c 'echo travail fini; exit 0'; sleep 45; kubectl get pod sage -n essai-relance; kubectl get pod sage -n essai-relance -o jsonpath='dernier code={.status.containerStatuses[0].lastState.terminated.exitCode} raison={.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text
pod/sage created
NAME   READY   STATUS      RESTARTS      AGE
sage   0/1     Completed   3 (33s ago)   45s
dernier code=0 raison=Completed
```

Three restarts, without any error: the last code is 0. A Pod restarts its
container as soon as it stops, even successfully (`restartPolicy: Always` by
default). A job that must finish and stop runs in a Job, not in a Pod or a
Deployment.

## 🧩 Exercise 3: command replaces the image's program

Start nginx giving it a command with `--command`, here `nginx -v`:

```bash
kubectl run entete --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-relance --command -- nginx -v; sleep 8; kubectl logs entete -n essai-relance; kubectl get pod entete -n essai-relance -o jsonpath='{.status.containerStatuses[0].state}{"\n"}' | cut -c1-80
```

```text
pod/entete created
nginx version: nginx/1.30.5
{"waiting":{"message":"back-off 10s restarting failed container=entete pod=entet
```

The container prints the version, exits, and goes into a loop. Look at what
the Pod holds:

```bash
kubectl get pod entete -n essai-relance -o jsonpath='command={.spec.containers[0].command} args={.spec.containers[0].args}{"\n"}'
```

```text
command=["nginx","-v"] args=
```

`command` replaces the image's entry point: nginx is not started as a server,
only the requested command runs. `args`, on the other hand, only completes the
entry point. A badly chosen `command` gives a container that "works" for one
second, then stops.

## 💬 Exercise 4: the termination message written by the container

A container can write an explanation to `/dev/termination-log` before it
stops. Kubernetes copies it into the Pod's state (here in French: "database
unreachable"):

```bash
cat <<YAML | kubectl apply -n essai-relance -f -
apiVersion: v1
kind: Pod
metadata:
  name: message
spec:
  restartPolicy: Never
  containers:
    - name: m
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo 'base injoignable : essai-db:5432' > /dev/termination-log; exit 2"]
YAML
sleep 10; kubectl get pod message -n essai-relance -o jsonpath='{.status.containerStatuses[0].state.terminated.message}{"\n"}'
```

```text
pod/message created
base injoignable : essai-db:5432
```

The message is readable without the logs, straight from the Pod's state. For
an application that writes nothing to that file,
`terminationMessagePolicy: FallbackToLogsOnError` takes the end of its logs
on error:

```bash
kubectl run message-journal --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-relance --restart=Never --overrides='{"spec":{"containers":[{"name":"m","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","echo derniere ligne du journal; exit 2"],"terminationMessagePolicy":"FallbackToLogsOnError"}]}}'; sleep 10; kubectl get pod message-journal -n essai-relance -o jsonpath='{.status.containerStatuses[0].state.terminated.message}{"\n"}'
```

```text
pod/message-journal created
derniere ligne du journal
```

The last log line became the termination message. This is useful when the
container's logs are already gone.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-relance
```

```text
namespace "essai-relance" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-troubleshoot-crashloop
dsoxlab check ckad-troubleshoot-crashloop
```

```text
╭─ Result: ckad-troubleshoot-crashloop ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests      │
╰───────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: three looping Pods, each for a different
reason, to get running again.

```bash
dsoxlab run ckad-troubleshoot-crashloop
dsoxlab challenge ckad-troubleshoot-crashloop
```
