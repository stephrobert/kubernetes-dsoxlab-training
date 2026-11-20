# Switch traffic from one version to another

A **Service** gives a fixed name and address to a group of Pods. It does not
pick its Pods by their name, but by their **labels**: that is its
**selector**. Changing this selector changes the Pods that receive the
traffic. That is the whole idea of a **blue-green** release: two versions run
at the same time, and the Service decides which one answers. The lesson shows
the switch. This course measures what happens during the seconds that follow
it, and what happens when you switch to a version that is not ready.

You work in a scratch namespace, `essai-bascule`, with a `boutique`
application in several versions. The challenge will ask you for the same work
on another application: you will do it on your own, at the end.

Related page: [Kubernetes Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-blue-green-deployment
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: run two versions at the same time

Each version is a Deployment of two Pods. Their container writes the name of
its version into a web page, then serves it with busybox's small `httpd`
server, on port 8080. A **readiness probe** (readinessProbe) checks every two
seconds that this port answers: a Pod only receives traffic if it is ready.
The Pods carry two labels: `app=boutique`, shared by every version, and
`version`, which tells them apart.

Create the scratch namespace, then `v1`:

```bash
kubectl create namespace essai-bascule
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boutique-v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boutique
      version: v1
  template:
    metadata:
      labels:
        app: boutique
        version: v1
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo v1 > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
          readinessProbe:
            tcpSocket:
              port: 8080
            periodSeconds: 2
YAML
```

```text
namespace/essai-bascule created
deployment.apps/boutique-v1 created
```

Create `v2` with the same manifest, replacing `v1` with `v2` in the four places
where it appears: the name, both `version` labels and the text served. Then
wait for both versions:

```bash
kubectl rollout status deployment/boutique-v1 -n essai-bascule --timeout=120s | tail -1
kubectl rollout status deployment/boutique-v2 -n essai-bascule --timeout=120s | tail -1
kubectl get pods -n essai-bascule -L version
```

```text
deployment "boutique-v1" successfully rolled out
deployment "boutique-v2" successfully rolled out
NAME                           READY   STATUS    RESTARTS   AGE   VERSION
boutique-v1-599bb57bc5-7m9zw   1/1     Running   0          1s    v1
boutique-v1-599bb57bc5-v8ttw   1/1     Running   0          1s    v1
boutique-v2-d57698b89-plf8q    1/1     Running   0          1s    v2
boutique-v2-d57698b89-xqcdw    1/1     Running   0          1s    v2
```

## 📚 Exercise 2: a Service that picks both versions

Create a `sonde` Pod to query the Service from inside the cluster, then the
`boutique` Service. It listens on port 80 and sends to port 8080 of the Pods.
Its selector only asks for `app=boutique`: it therefore picks the Pods of both
versions.

```bash
kubectl run sonde \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  --restart=Never -n essai-bascule -- sleep 3600
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: v1
kind: Service
metadata:
  name: boutique
spec:
  selector:
    app: boutique
  ports:
    - port: 80
      targetPort: 8080
YAML
kubectl wait --for=condition=Ready pod/sonde -n essai-bascule --timeout=60s
```

```text
pod/sonde created
service/boutique created
pod/sonde condition met
```

The addresses of the Pods picked by the Service are called its **endpoints**.
Keep in a variable the command that prints them, with whether each one is
ready, then send eight requests:

```bash
EP='{range .items[*].endpoints[*]}{.addresses[0]} pret={.conditions.ready}{"\n"}{end}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
10.244.38.100 pret=true
10.244.163.15 pret=true
10.244.38.96 pret=true
10.244.163.14 pret=true
v2
v1
v1
v1
v2
v1
v2
v2
```

Four ready endpoints, and answers that mix both versions. Port 80 does not
show in the address: it is HTTP's default port.

## 📚 Exercise 3: keep only one version

`kubectl set selector` replaces the **whole** selector of a Service. Give it
`version=v1` on top of `app=boutique`:

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
service/boutique selector updated
10.244.38.100 pret=true
10.244.163.15 pret=true
v1
v1
v1
v1
v1
v1
v1
v1
```

Two endpoints, and eight `v1` answers. `v2` still runs, but no longer
receives anything.

## 📚 Exercise 4: switch, and measure the seconds that follow

The switch only changes one key of the selector. `kubectl patch` changes that
key alone and keeps the others, while `set selector` rewrites everything:

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v2"}}}'
kubectl get service boutique -n essai-bascule -o jsonpath='{.spec.selector}{"\n"}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
service/boutique patched
{"app":"boutique","version":"v2"}
10.244.38.96 pret=true
10.244.163.14 pret=true
v1
v1
v1
v2
v2
v2
v2
v2
```

The selector keeps `app=boutique`, and the endpoints are already those of
`v2`. Yet the first three requests still answer `v1`. The list of endpoints
changes at once in the API. But each node must then apply this list to its
network rules, and that takes a few seconds. Meanwhile, the old version still
receives traffic: one more reason not to stop it right after the switch. The
Pods of both versions still run:

```bash
kubectl get pods -n essai-bascule -l app=boutique -L version
```

```text
NAME                           READY   STATUS    RESTARTS   AGE   VERSION
boutique-v1-599bb57bc5-7m9zw   1/1     Running   0          5s    v1
boutique-v1-599bb57bc5-v8ttw   1/1     Running   0          5s    v1
boutique-v2-d57698b89-plf8q    1/1     Running   0          5s    v2
boutique-v2-d57698b89-xqcdw    1/1     Running   0          5s    v2
```

## 📚 Exercise 5: the rollback

Going back is the same patch, with the old value:

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v1"}}}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 "http://boutique"; done
```

```text
service/boutique patched
10.244.38.100 pret=true
10.244.163.15 pret=true
v2
v2
v2
v2
v2
v2
v2
v1
```

Same delay, the other way round: seven requests still go to `v2`, then `v1`
takes over. The delay varies from one try to the next: check a switch a few
seconds after making it, not right away.

## 📚 Exercise 6: switch to a version that is not ready

Create a `v3` that starts, but whose readiness probe targets port 9999, where
nothing listens. Reuse the `v1` manifest, with `v3` in the same four places,
and `port: 9999` in `readinessProbe`. After about fifteen seconds, look at it
**before** switching:

```bash
kubectl get pods -n essai-bascule -l version=v3
kubectl get deployment boutique-v3 -n essai-bascule
```

```text
NAME                           READY   STATUS    RESTARTS   AGE
boutique-v3-5cf759fd9f-hs2f9   0/1     Running   0          15s
boutique-v3-5cf759fd9f-vpg78   0/1     Running   0          15s
NAME          READY   UP-TO-DATE   AVAILABLE   AGE
boutique-v3   0/2     2            0           15s
```

The Pods run (`Running`), but none is ready (`0/1`), and the Deployment has no
available Pod. Switch anyway, to see:

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v3"}}}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique
```

```text
service/boutique patched
10.244.38.93 pret=false
10.244.163.16 pret=false
wget: can't connect to remote host (10.109.37.21): Connection refused
command terminated with exit code 1
```

The Service did find both Pods of `v3`, but they are marked `pret=false`, and
a Service sends nothing to an endpoint that is not ready. The whole
application is cut off. Go back to `v1`:

```bash
kubectl patch service boutique -n essai-bascule -p '{"spec":{"selector":{"version":"v1"}}}'
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique -o jsonpath="$EP"
kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique
```

```text
service/boutique patched
10.244.38.100 pret=true
10.244.163.15 pret=true
v1
```

Before a switch, check the target: the `READY` column of the Pods and the
`AVAILABLE` column of the Deployment.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace,
with everything in it.

```bash
kubectl delete namespace essai-bascule
```

```text
namespace "essai-bascule" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

```text
╭─ Result: ckad-blue-green-deployment ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/10 tests    │
╰──────────────────────────────────────╯
```

0 out of 10: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: run two versions of an application, then
switch its Service from one to the other, without stopping the old one.

```bash
dsoxlab run ckad-blue-green-deployment
dsoxlab challenge ckad-blue-green-deployment
```
