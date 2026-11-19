# Wait for a dependency with an init container

An **init container** is a container that runs **before** the main containers
of a Pod, all the way through. As long as it has not succeeded, the main
containers do not start. You use it to prepare something, or to wait until a
dependency answers. In this course, you write an init container that prepares
a file, you see that a Service can exist with nobody behind it, you make a Pod
wait, you bring in its dependency, then you see what happens when an init
container fails.

You work in a scratch namespace, `essai-init`, with a `boutique` ("shop")
application that waits for a `stock-svc` service. The challenge will ask you
for the same thing with other names, in another namespace: you will do it on
your own, at the end.

Related page: [Init containers and sidecars](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/init-containers-and-sidecars/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-init-container
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: an init container that succeeds

Create the scratch namespace, then a `preparation` Pod. Its init container
`ecrire-page` ("write page") writes a page into a shared volume (`emptyDir`).
The main container `web`, an nginx, serves that same volume. Init containers
are declared under `initContainers`, next to `containers`:

```bash
kubectl create namespace essai-init
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: preparation
spec:
  initContainers:
    - name: ecrire-page
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo page preparee par l init container > /travail/index.html"]
      volumeMounts:
        - name: travail
          mountPath: /travail
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      volumeMounts:
        - name: travail
          mountPath: /usr/share/nginx/html
  volumes:
    - name: travail
      emptyDir: {}
YAML
```

```text
namespace/essai-init created
pod/preparation created
```

Wait until the Pod is ready:

```bash
kubectl wait --for=condition=Ready pod/preparation -n essai-init --timeout=120s; kubectl get pod preparation -n essai-init
```

```text
pod/preparation condition met
NAME          READY   STATUS    RESTARTS   AGE
preparation   1/1     Running   0          1s
```

`READY 1/1` only counts the main container. The state of the init container is
read in `status.initContainerStatuses`:

```bash
kubectl get pod preparation -n essai-init -o jsonpath='{.status.initContainerStatuses[0].name} {.status.initContainerStatuses[0].state.terminated.reason} {.status.initContainerStatuses[0].state.terminated.exitCode}{"\n"}'
```

```text
ecrire-page Completed 0
```

It has finished (`Completed`), with code 0. The main container does serve the
page it wrote ("page prepared by the init container"):

```bash
kubectl exec preparation -n essai-init -c web -- cat /usr/share/nginx/html/index.html
```

```text
page preparee par l init container
```

## 📚 Exercise 2: a Service with nobody behind it

Create a `stock-svc` Service that selects the `app=stock` Pods.
`kubectl create service` sets the selector `app: stock-svc` by default: `sed`
replaces it with `app: stock` before sending it:

```bash
kubectl create service clusterip stock-svc --tcp=80:80 -n essai-init -o yaml --dry-run=client | sed 's/app: stock-svc/app: stock/' | kubectl apply -f - -n essai-init
kubectl get endpointslices -n essai-init -l kubernetes.io/service-name=stock-svc
```

```text
service/stock-svc created
NAME              ADDRESSTYPE   PORTS     ENDPOINTS   AGE
stock-svc-jhcjx   IPv4          <unset>   <unset>     0s
```

No Pod carries `app=stock`: the Service has no address behind it (`<unset>`).
Start a throwaway Pod that queries this Service by its DNS name, then over HTTP
(`--rm` deletes it at the end):

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-init --rm -i --quiet -- sh -c 'nslookup stock-svc.essai-init.svc.cluster.local | tail -3; wget -qO- -T 3 http://stock-svc/ || echo "wget : code $?"'
```

```text
Name:	stock-svc.essai-init.svc.cluster.local
Address: 10.100.162.100

wget: can't connect to remote host (10.100.162.100): Connection refused
wget : code 1
```

The name resolves: the Service exists in DNS as soon as it is created. But the
HTTP request is refused, because nobody answers behind it. So waiting for the
name to resolve waits for nothing. You must wait for an **answer**.

## 📚 Exercise 3: an init container that waits

Create the `boutique` Pod. Its init container `attendre-stock` ("wait for
stock") repeats an HTTP request to `stock-svc` every 3 seconds
(`until … do … done`), until it succeeds:

```bash
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: boutique
spec:
  initContainers:
    - name: attendre-stock
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "until wget -qO- -T 2 http://stock-svc/ > /dev/null; do echo stock-svc ne repond pas encore; sleep 3; done; echo stock-svc repond"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
pod/boutique created
```

After 15 seconds, look at the Pod:

```bash
sleep 15; kubectl get pod boutique -n essai-init
```

```text
NAME       READY   STATUS     RESTARTS   AGE
boutique   0/1     Init:0/1   0          15s
```

`Init:0/1`: 0 init container finished out of 1. Its logs show it is waiting
("stock-svc does not answer yet"):

```bash
kubectl logs boutique -n essai-init -c attendre-stock | tail -3
```

```text
stock-svc ne repond pas encore
wget: can't connect to remote host (10.100.162.100): Connection refused
stock-svc ne repond pas encore
```

And the main container has not started at all:

```bash
kubectl logs boutique -n essai-init -c web 2>&1 | tail -1
```

```text
Error from server (BadRequest): container "web" in pod "boutique" is waiting to start: PodInitializing
```

## 📚 Exercise 4: the dependency arrives

Start an nginx Pod `stock` with the `app=stock` label:

```bash
kubectl run stock --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --labels=app=stock --port=80 -n essai-init; kubectl wait --for=condition=Ready pod/stock -n essai-init --timeout=120s
kubectl get endpointslices -n essai-init -l kubernetes.io/service-name=stock-svc
```

```text
pod/stock created
pod/stock condition met
NAME              ADDRESSTYPE   PORTS   ENDPOINTS      AGE
stock-svc-jhcjx   IPv4          80      10.244.38.87   20s
```

The Service now has an address. Without touching anything else, wait until
`boutique` is ready:

```bash
kubectl wait --for=condition=Ready pod/boutique -n essai-init --timeout=120s; kubectl get pod boutique -n essai-init
```

```text
pod/boutique condition met
NAME       READY   STATUS    RESTARTS   AGE
boutique   1/1     Running   0          17s
```

The init container saw the answer, finished, and the main container started
("stock-svc answers"):

```bash
kubectl logs boutique -n essai-init -c attendre-stock | tail -2
kubectl get pod boutique -n essai-init -o jsonpath='{.status.initContainerStatuses[0].state.terminated.reason} {.status.initContainerStatuses[0].state.terminated.exitCode}{"\n"}'
```

```text
stock-svc ne repond pas encore
stock-svc repond
Completed 0
```

## 📚 Exercise 5: an init container that fails

What happens if the init container exits with an error? Create a `rate`
("failed") Pod whose init container exits with code 1:

```bash
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: rate
spec:
  initContainers:
    - name: verifier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo verification impossible; exit 1"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
pod/rate created
```

After 25 seconds:

```bash
sleep 25; kubectl get pod rate -n essai-init
kubectl get pod rate -n essai-init -o jsonpath='{.status.initContainerStatuses[0].restartCount}{"\n"}'; kubectl logs rate -n essai-init -c verifier
```

```text
NAME   READY   STATUS       RESTARTS      AGE
rate   0/1     Init:Error   2 (24s ago)   25s
2
verification impossible
```

`Init:Error`: the init container failed. Kubernetes starts it again (already 2
times), and the main container keeps waiting. So an init container must
**succeed** for the Pod to start. That is what lets you hold an application
back as long as its dependency is missing.

## 🧹 Clean up

Delete the scratch namespace, and everything in it:

```bash
kubectl delete namespace essai-init
```

```text
namespace "essai-init" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-init-container
dsoxlab check ckad-init-container
```

```text
╭─── Result: ckad-init-container ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another application, which must wait for its
configuration server before starting.

```bash
dsoxlab run ckad-init-container
dsoxlab challenge ckad-init-container
```
