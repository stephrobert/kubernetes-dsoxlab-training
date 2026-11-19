# Three probes on one Pod: startup, liveness, readiness

Kubernetes does not know, on its own, whether an application works. It asks
**probes**: checks it repeats, whose result decides what it does.

- The **readiness** probe says whether the Pod can receive traffic.
- The **liveness** probe says whether the container must be restarted.
- The **startup** probe gives a slow application time to start, before the
  other two begin.

In this course, you see each of them fail, then succeed.

You work in a scratch namespace, `essai-sondes`, with the `vitrine`,
`gardien`, `lent-court` ("slow-short") and `lent-patient` ("slow-patient")
Pods. The challenge will ask you for all three probes on another application,
in another namespace: you will do it on your own, at the end.

Related page: [Probes](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/probes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-probes-all-types
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a readiness probe that fails

Create the scratch namespace and an nginx `vitrine` Pod. Its readiness probe
asks for the `/pret.html` page every 3 seconds. That page does not exist yet.
`kubectl expose` creates a Service in front of the Pod:

```bash
kubectl create namespace essai-sondes
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: vitrine
  labels:
    app: vitrine
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      ports:
        - containerPort: 80
      readinessProbe:
        httpGet:
          path: /pret.html
          port: 80
        periodSeconds: 3
YAML
kubectl expose pod vitrine --port=80 -n essai-sondes
```

```text
namespace/essai-sondes created
pod/vitrine created
service/vitrine exposed
```

15 seconds later:

```bash
sleep 15; kubectl get pod vitrine -n essai-sondes
```

```text
NAME      READY   STATUS    RESTARTS   AGE
vitrine   0/1     Running   0          15s
```

`Running`, but `0/1`: the container runs, and it is not ready. The events say
why (`Unhealthy` is the reason given for a probe failure):

```bash
kubectl get events -n essai-sondes --field-selector involvedObject.name=vitrine,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2
```

```text
Readiness probe failed: Get "http://10.244.38.69:80/pret.html": dial tcp 10.244.38.69:80: connect: connection refused
Readiness probe failed: HTTP probe failed with statuscode: 404
```

First `connection refused` (nginx was starting), then `404`: the page does not
exist. The effect on traffic: the Service knows the Pod's address, but marks it
as not ready.

```bash
kubectl get endpointslices -n essai-sondes -l kubernetes.io/service-name=vitrine -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{"\n"}{end}'
```

```text
10.244.38.69 ready=false
```

The Service will send nothing to this Pod as long as it is not ready.

## 📚 Exercise 2: readiness follows the application

Create the page the probe expects, then look at the Pod 6 seconds later:

```bash
kubectl exec vitrine -n essai-sondes -- sh -c 'echo pret > /usr/share/nginx/html/pret.html'; sleep 6; kubectl get pod vitrine -n essai-sondes
kubectl get endpointslices -n essai-sondes -l kubernetes.io/service-name=vitrine -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{"\n"}{end}'
```

```text
NAME      READY   STATUS    RESTARTS   AGE
vitrine   1/1     Running   0          21s
10.244.38.69 ready=true
```

The Pod is ready, and the Service can send it traffic. Remove the page:

```bash
kubectl exec vitrine -n essai-sondes -- rm /usr/share/nginx/html/pret.html; sleep 12; kubectl get pod vitrine -n essai-sondes
```

```text
NAME      READY   STATUS    RESTARTS   AGE
vitrine   0/1     Running   0          34s
```

Back to `0/1`, but `RESTARTS 0`: the readiness probe never restarts the
container. It only takes it out of traffic, and puts it back as soon as it
answers.

## 📚 Exercise 3: a liveness probe that restarts the container

A probe is not always HTTP. The `exec` type runs a command in the container:
the probe succeeds if the command exits with code 0. The `gardien` ("guard")
Pod creates a `/tmp/vivant` ("alive") file at start, and its liveness probe
checks that it exists. After 2 failures 3 seconds apart, the container is
restarted. `terminationGracePeriodSeconds: 2` shortens the stop delay: without
it, Kubernetes would wait 30 seconds, because `sleep` started by `sh` ignores
the stop request.

```bash
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: gardien
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: veille
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "touch /tmp/vivant; sleep 3600"]
      livenessProbe:
        exec:
          command: ["cat", "/tmp/vivant"]
        periodSeconds: 3
        failureThreshold: 2
YAML
kubectl wait --for=condition=Ready pod/gardien -n essai-sondes --timeout=60s; kubectl get pod gardien -n essai-sondes
```

```text
pod/gardien created
pod/gardien condition met
NAME      READY   STATUS    RESTARTS   AGE
gardien   1/1     Running   0          0s
```

Delete the file, as if the application had frozen, then wait 20 seconds:

```bash
kubectl exec gardien -n essai-sondes -- rm /tmp/vivant; sleep 20; kubectl get pod gardien -n essai-sondes
```

```text
NAME      READY   STATUS    RESTARTS      AGE
gardien   1/1     Running   1 (12s ago)   20s
```

`RESTARTS 1`: the container was restarted. On restart, its command created the
file again, and it is healthy once more. The events tell the failure then the
restart:

```bash
kubectl get events -n essai-sondes --field-selector involvedObject.name=gardien,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2; kubectl get events -n essai-sondes --field-selector involvedObject.name=gardien,reason=Killing -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2
```

```text

Liveness probe failed: cat: can't open '/tmp/vivant': No such file or directory
Container veille failed liveness probe, will be restarted
```

## 📚 Exercise 4: a slow application, a startup probe too short

The `lent-court` Pod simulates an application that takes 20 seconds to start:
it waits, then starts a small web server on port 8080. Its startup probe tries
every 2 seconds, and gives up after 3 failures. So it tolerates
2 × 3 = **6 seconds**:

```bash
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent-court
spec:
  containers:
    - name: web
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo demarrage lent; sleep 20; mkdir -p /www; echo ok > /www/index.html; httpd -f -p 8080 -h /www"]
      startupProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 2
        failureThreshold: 3
      livenessProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 10
YAML
```

```text
pod/lent-court created
```

45 seconds later:

```bash
sleep 45; kubectl get pod lent-court -n essai-sondes
kubectl get events -n essai-sondes --field-selector involvedObject.name=lent-court,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2; kubectl get events -n essai-sondes --field-selector involvedObject.name=lent-court,reason=Killing -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2
```

```text
NAME         READY   STATUS    RESTARTS     AGE
lent-court   0/1     Running   1 (9s ago)   45s
Startup probe failed: Get "http://10.244.38.127:8080/": dial tcp 10.244.38.127:8080: connect: connection refused
Container web failed startup probe, will be restarted
```

After 6 seconds without an answer, the startup probe gave up, and Kubernetes
restarted the container. On restart, the application starts its 20-second wait
again, and will be restarted again: it will never start. As long as the
startup probe has not succeeded, the liveness probe does not run.

## 📚 Exercise 5: the same application, a patient startup probe

Same application, but 20 failures allowed: 2 × 20 = **40 seconds** of
tolerance, enough to cover the 20 seconds of startup:

```bash
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent-patient
spec:
  containers:
    - name: web
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo demarrage lent; sleep 20; mkdir -p /www; echo ok > /www/index.html; httpd -f -p 8080 -h /www"]
      startupProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 2
        failureThreshold: 20
      livenessProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 10
YAML
```

```text
pod/lent-patient created
```

```bash
kubectl wait --for=condition=Ready pod/lent-patient -n essai-sondes --timeout=90s; kubectl get pod lent-patient -n essai-sondes
kubectl get pod lent-patient -n essai-sondes -o jsonpath='demarre={.status.containerStatuses[0].started} pret={.status.containerStatuses[0].ready} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'
```

```text
pod/lent-patient condition met
NAME           READY   STATUS    RESTARTS   AGE
lent-patient   1/1     Running   0          22s
demarre=true pret=true redemarrages=0
```

Ready after 22 seconds, with no restart at all (`demarre` means "started",
`pret` "ready", `redemarrages` "restarts"). `started=true` says the startup
probe succeeded: the liveness probe took over.

## 🧹 Clean up

Delete the scratch namespace, with its Pods and its Service:

```bash
kubectl delete namespace essai-sondes
```

```text
namespace "essai-sondes" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-probes-all-types
dsoxlab check ckad-probes-all-types
```

```text
╭── Result: ckad-probes-all-types ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: all three probes on another application,
with enough patience for a slow start.

```bash
dsoxlab run ckad-probes-all-types
dsoxlab challenge ckad-probes-all-types
```
