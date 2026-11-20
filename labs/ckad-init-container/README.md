# Repair the gatekeeper of an application with an init container

An **init container** is a container that runs **before** the main containers
of a Pod, all the way through. As long as it has not succeeded, the main
containers do not start. You use it to prepare something, or to wait until a
dependency answers. In this course, you see what happens to a Pod whose init
container fails, depending on whether it is restarted or not. You also see
that a Service can exist with nobody behind it. Then you write a bounded
wait, let it expire, and bring in the dependency.

You work in a scratch namespace, `essai-init`, with a `boutique` ("shop")
application that waits for a `stock-svc` service. The challenge is about
another application, in another namespace: you will do it on your own, at
the end.

Related page: [Init containers and sidecars](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/init-containers-and-sidecars/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-init-container
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: an init container that fails, with no restart

Create the scratch namespace, then a Pod `unique` ("single"). Its init
container `verifier` ("check") exits with code 3. The Pod declares
`restartPolicy: Never`: nothing in it is restarted. Init containers are
declared under `initContainers`, next to `containers`:

```bash
kubectl create namespace essai-init
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Pod
metadata:
  name: unique
spec:
  restartPolicy: Never
  initContainers:
    - name: verifier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo verification impossible; exit 3"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
namespace/essai-init created
apiVersion: v1
kind: Pod
metadata:
  name: unique
spec:
  restartPolicy: Never
  initContainers:
    - name: verifier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo verification impossible; exit 3"]
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
pod/unique created
```

After 10 seconds:

```bash
sleep 10; kubectl get pod unique -n essai-init
```

```text
NAME     READY   STATUS       RESTARTS   AGE
unique   0/1     Init:Error   0          10s
```

`Init:Error`: the init container failed. The phase of the Pod, the exit code
and the number of restarts are in its status:

```bash
kubectl get pod unique -n essai-init -o jsonpath='{.status.phase} {.status.initContainerStatuses[0].state.terminated.exitCode} {.status.initContainerStatuses[0].restartCount}{"\n"}'
```

```text
Failed 3 0
```

The Pod is in phase `Failed`, with code 3 and no restart. 20 seconds later,
nothing has moved:

```bash
sleep 20; kubectl get pod unique -n essai-init
```

```text
NAME     READY   STATUS       RESTARTS   AGE
unique   0/1     Init:Error   0          30s
```

With `restartPolicy: Never`, a failed init container makes the whole Pod
fail, for good. The `web` container will never start.

## 📚 Exercise 2: a Service with nobody behind it

Create a `stock-svc` Service that selects the `app=stock` Pods, on port 80:

```bash
cat <<'YAML' | kubectl apply -n essai-init -f -
apiVersion: v1
kind: Service
metadata:
  name: stock-svc
spec:
  selector:
    app: stock
  ports:
    - port: 80
      targetPort: 80
YAML
kubectl get endpointslices -n essai-init -l kubernetes.io/service-name=stock-svc
```

```text
apiVersion: v1
kind: Service
metadata:
  name: stock-svc
spec:
  selector:
    app: stock
  ports:
    - port: 80
      targetPort: 80
YAML
service/stock-svc created
NAME              ADDRESSTYPE   PORTS     ENDPOINTS   AGE
stock-svc-qb8zx   IPv4          <unset>   <unset>     0s
```

No Pod carries `app=stock`: the Service has no address behind it (`<unset>`).
Start a throwaway Pod that queries this Service by its DNS name, then over HTTP
(`--rm` deletes it at the end):

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-init --rm -i --quiet -- sh -c 'nslookup stock-svc.essai-init.svc.cluster.local | tail -3; wget -qO- -T 3 http://stock-svc/ || echo "wget : code $?"'
```

```text
Name:	stock-svc.essai-init.svc.cluster.local
Address: 10.100.1.209

wget: can't connect to remote host (10.100.1.209): Connection refused
wget : code 1
```

The name resolves: the Service exists in DNS as soon as it is created. But the
HTTP request is refused, because nobody answers behind it. So waiting for the
name to resolve waits for nothing. You must wait for an **answer**.

## 📚 Exercise 3: a bounded wait that expires

Create the `boutique` Pod. Its init container `attendre-stock` ("wait for
stock") queries `stock-svc` over HTTP 5 times, 2 seconds apart. It exits with
code 0 as soon as a request succeeds, and with code 1 after the fifth failure.
A wait with no limit would never end, and nothing would report the problem:

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
      command:
        - sh
        - -c
        - |
          for i in 1 2 3 4 5; do
            wget -qO- -T 2 http://stock-svc/ > /dev/null && echo stock-svc repond && exit 0
            echo essai $i : stock-svc ne repond pas
            sleep 2
          done
          echo abandon apres 5 essais
          exit 1
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
```

```text
apiVersion: v1
kind: Pod
metadata:
  name: boutique
spec:
  initContainers:
    - name: attendre-stock
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command:
        - sh
        - -c
        - |
          for i in 1 2 3 4 5; do
            wget -qO- -T 2 http://stock-svc/ > /dev/null && echo stock-svc repond && exit 0
            echo essai $i : stock-svc ne repond pas
            sleep 2
          done
          echo abandon apres 5 essais
          exit 1
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
pod/boutique created
```

After 25 seconds, look at the Pod:

```bash
sleep 25; kubectl get pod boutique -n essai-init
```

```text
NAME       READY   STATUS     RESTARTS      AGE
boutique   0/1     Init:0/1   1 (10s ago)   25s
```

`Init:0/1`: 0 init container finished out of 1. The `RESTARTS` column says the
init container has already been restarted once: the first wait expired. This
Pod has no `restartPolicy`, so it is `Always`, and Kubernetes restarts the
failed init container. `--previous` shows the logs of the attempt before
("abandon apres 5 essais" means "giving up after 5 tries"):

```bash
kubectl logs boutique -n essai-init -c attendre-stock --previous | tail -2
```

```text
wget: can't connect to remote host (10.100.1.209): Connection refused
abandon apres 5 essais
```

40 seconds later:

```bash
sleep 40; kubectl get pod boutique -n essai-init
```

```text
NAME       READY   STATUS       RESTARTS      AGE
boutique   0/1     Init:Error   2 (34s ago)   65s
```

A second wait expired, and the Pod shows `Init:Error`. The restart counter
and the code of the last exit confirm it:

```bash
kubectl get pod boutique -n essai-init -o jsonpath='{.status.initContainerStatuses[0].restartCount} {.status.initContainerStatuses[0].lastState.terminated.exitCode}{"\n"}'
```

```text
2 1
```

A bounded wait shows: the Pod goes into error and its restarts add up. A wait
with no limit would stay in `Init:0/1` forever, with no restart at all.

## 📚 Exercise 4: the dependency arrives

Start an nginx Pod `stock` with the `app=stock` label:

```bash
kubectl run stock --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --labels=app=stock --port=80 -n essai-init; kubectl wait --for=condition=Ready pod/stock -n essai-init --timeout=120s
```

```text
pod/stock created
pod/stock condition met
```

The Service now has an address. Without touching anything else, wait until
`boutique` is ready. Depending on when the init container is restarted, it
can take more than a minute:

```bash
kubectl wait --for=condition=Ready pod/boutique -n essai-init --timeout=300s; kubectl get pod boutique -n essai-init
```

```text
pod/boutique condition met
NAME       READY   STATUS    RESTARTS   AGE
boutique   1/1     Running   0          89s
```

The next restart found `stock-svc` answering, the init container finished
and the main container started. The `RESTARTS` column is back to 0: once the
Pod has started, it only counts the main containers. The logs of the last
attempt ("repond" means "answers"):

```bash
kubectl logs boutique -n essai-init -c attendre-stock | tail -2
```

```text
stock-svc repond
```

## 📚 Exercise 5: an init container that fails, with restarts

Compare with exercise 1. Create a `rate` ("failed") Pod whose init container
exits with code 1, with no `restartPolicy`, so `Always`:

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

The same `Init:Error` as in exercise 1, but this time Kubernetes restarts the
init container (already 2 times), and the Pod has not failed for good. An init
container must **succeed** for the Pod to start: that is what lets you hold an
application back as long as its dependency is missing.

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

Your turn, on your own this time: an application already runs although its
dependency does not answer. Its gatekeeper held nothing back: find out why,
and repair it.

```bash
dsoxlab run ckad-init-container
dsoxlab challenge ckad-init-container
```
