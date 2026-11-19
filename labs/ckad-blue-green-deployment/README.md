# Switch traffic from one version to another

A **Service** gives a fixed name and address to a group of Pods. It does not
pick its Pods by name, but by their **labels**: that is its **selector**.
Changing the selector changes, within a few seconds, which Pods receive the
traffic. That is the whole idea of a **blue-green** release: two versions run
at the same time, and the Service decides which one answers. In this course,
you run two versions, you mix then separate their traffic, you switch, then you
roll back.

You work in a scratch namespace, `essai-bascule`, with a `boutique` application
in two versions, `v1` and `v2`. The challenge will ask you for the same work on
another application: you will do it on your own, at the end.

Related page: [Kubernetes Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-blue-green-deployment
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: run two versions at the same time

Create the scratch namespace:

```bash
kubectl create namespace essai-bascule
```

```text
namespace/essai-bascule created
```

Each version is a Deployment of two Pods. Their container writes the name of
its version into a web page, then serves it with the small busybox `httpd`
server, on port 8080. The Pods carry two labels: `app=boutique`, shared by both
versions, and `version`, which tells them apart. Create `v1`:

```bash
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
          command: ["sh", "-c", "echo v1 > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - containerPort: 8080
YAML
```

```text
deployment.apps/boutique-v1 created
```

Then `v2`, identical except for three details: its name, its `version` label
and the text it answers.

```bash
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boutique-v2
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boutique
      version: v2
  template:
    metadata:
      labels:
        app: boutique
        version: v2
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo v2 > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - containerPort: 8080
YAML
```

```text
deployment.apps/boutique-v2 created
```

Wait until both are ready, then show the Pods with their labels as columns
(`-L`):

```bash
kubectl rollout status deployment/boutique-v1 -n essai-bascule --timeout=120s | tail -1
kubectl rollout status deployment/boutique-v2 -n essai-bascule --timeout=120s | tail -1
kubectl get pods -n essai-bascule -L app,version
```

```text
deployment "boutique-v1" successfully rolled out
deployment "boutique-v2" successfully rolled out
NAME                           READY   STATUS    RESTARTS   AGE   APP        VERSION
boutique-v1-86cc57db9f-vf7ps   1/1     Running   0          4s    boutique   v1
boutique-v1-86cc57db9f-z95c6   1/1     Running   0          4s    boutique   v1
boutique-v2-869bb4f44c-7vxms   1/1     Running   0          4s    boutique   v2
boutique-v2-869bb4f44c-mpqcm   1/1     Running   0          4s    boutique   v2
```

Four Pods, all `app=boutique`, two on `v1` and two on `v2`.

## 📚 Exercise 2: a Service that picks its Pods by their labels

To query the Service from inside the cluster, you need a Pod. Create a `sonde`
Pod that only sleeps:

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-bascule -- sleep 3600
```

```text
pod/sonde created
```

Now create the `boutique` Service. Its selector only asks for `app=boutique`:
it therefore picks the Pods of both versions.

```bash
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: v1
kind: Service
metadata:
  name: boutique
spec:
  selector:
    app: boutique
  ports:
    - port: 8080
      targetPort: 8080
YAML
```

```text
service/boutique created
```

Wait until the probe is ready, then send eight requests to the Service, by its
name, from the probe:

```bash
kubectl wait --for=condition=Ready pod/sonde -n essai-bascule --timeout=60s
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
pod/sonde condition met
v2
v1
v2
v1
v2
v1
v1
v1
```

The answers mix: the Service spreads the requests over the four Pods. The
addresses of the Pods it picked are its **endpoints**. They show in an
`EndpointSlice` object:

```bash
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique
```

```text
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                                              AGE
boutique-2llhn   IPv4          8080    10.244.38.99,10.244.163.34,10.244.38.100 + 1 more...   2s
```

Four addresses: three shown, and "1 more", the fourth one.

## 📚 Exercise 3: keep a single version

`kubectl set selector` replaces the selector of a Service. Add `version=v1` to
it:

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
kubectl get service boutique -n essai-bascule -o jsonpath='{.spec.selector}{"\n"}'
```

```text
service/boutique selector updated
{"app":"boutique","version":"v1"}
```

The Service now only picks the Pods that have **both** labels. Give it three
seconds to update its endpoints, then run the eight requests again:

```bash
sleep 3; for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
v1
v1
v1
v1
v1
v1
v1
v1
```

Eight answers out of eight come from `v1`. `v2` is still running, but no longer
receives anything.

## 📚 Exercise 4: the switch

Putting `v2` into production means changing a single value of the selector:

```bash
kubectl set selector service boutique 'app=boutique,version=v2' -n essai-bascule
sleep 3; for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
service/boutique selector updated
v2
v2
v2
v2
v2
v2
v2
v2
```

All the traffic moved to `v2` at once. No Pod was created or deleted: all four
are still running.

```bash
kubectl get pods -n essai-bascule -l app=boutique -L version
```

```text
NAME                           READY   STATUS    RESTARTS   AGE   VERSION
boutique-v1-86cc57db9f-vf7ps   1/1     Running   0          13s   v1
boutique-v1-86cc57db9f-z95c6   1/1     Running   0          13s   v1
boutique-v2-869bb4f44c-7vxms   1/1     Running   0          13s   v2
boutique-v2-869bb4f44c-mpqcm   1/1     Running   0          13s   v2
```

That is what makes blue-green safe: the old version stays ready to take over
again.

## 📚 Exercise 5: the rollback

`v2` has a problem? Rolling back is the same command, with the old value:

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
sleep 3; for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
service/boutique selector updated
v1
v1
v1
v1
v1
v1
v1
v1
```

The rollback is immediate, because the `v1` Pods never stopped running. Had you
deleted `v1` after the switch, you would have to wait for new Pods to start.

## 📚 Exercise 6: a selector that picks nobody

One typo in the selector, and the Service finds no Pod at all. Try with a
version that does not exist, `v3`:

```bash
kubectl set selector service boutique 'app=boutique,version=v3' -n essai-bascule
sleep 3; kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique
```

```text
service/boutique selector updated
NAME             ADDRESSTYPE   PORTS     ENDPOINTS   AGE
boutique-2llhn   IPv4          <unset>   <unset>     16s
```

No endpoint left. A request is then refused:

```bash
kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique:8080
```

```text
wget: can't connect to remote host (10.100.228.214): Connection refused
command terminated with exit code 1
```

The Service still exists, with its address (`10.100.228.214`), but it has
nobody to pass the request to. To find the cause, look for Pods with the same
selector:

```bash
kubectl get pods -n essai-bascule -l 'app=boutique,version=v3'
```

```text
No resources found in essai-bascule namespace.
```

No Pod carries these labels: the selector is wrong. Fix it:

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
sleep 3; kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique:8080
```

```text
service/boutique selector updated
v1
```

## 🧹 Clean up

Delete the scratch namespace, with everything in it:

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
