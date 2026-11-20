# Deploy, expose and scale a first application

The lesson deploys an application, exposes it through a Service and scales
it. This course makes you diagnose what happens when one of these moves goes
wrong, then move to a file that `kubectl diff` reads before each
`kubectl apply`.

A few words come back all along:

- a **Pod** is the smallest unit Kubernetes runs: one or more containers;
- a **Deployment** says "I want N Pods of this image", and Kubernetes creates
  them and replaces them if they fall;
- a **Service** gives a stable address to reach those Pods, even when they
  change;
- a **namespace** is a storage space inside the cluster.

You work in a scratch namespace, `essai-web`, with an application named
`accueil`. The challenge will ask you for another application, in another
namespace: you will deploy it on your own, at the end.

Related page: [Deploy your first application](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/fundamentals/first-deployment/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-premier-deploiement
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, on Kubernetes `v1.37.0`, and your kubectl already
targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: create in a namespace that does not exist

Start the `accueil` application in the `essai-web` namespace, without having
created it:

```bash
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web
```

```text
error: failed to create deployment: namespaces "essai-web" not found
```

Kubernetes does not create the namespace for you. Create it, then run the same
command again and wait until the application is available:

```bash
kubectl create namespace essai-web
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
```

```text
namespace/essai-web created
deployment.apps/accueil created
deployment.apps/accueil condition met
```

To query the application from inside the cluster, start an `outil` Pod that
stays up for one hour. The busybox image holds the `wget` command:

```bash
kubectl run outil \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  -n essai-web -- sleep 3600
kubectl wait --for=condition=Ready pod/outil -n essai-web --timeout=120s
```

```text
pod/outil created
pod/outil condition met
```

`kubectl exec outil -- <command>` runs a command in this Pod. You use it in
the next exercises.

## 📚 Exercise 2: a Service that finds the Pod but targets the wrong port

Expose `accueil` on port `8080`, without giving `--target-port`:

```bash
kubectl expose deployment accueil --port=8080 -n essai-web
kubectl get endpointslice -n essai-web -l kubernetes.io/service-name=accueil
```

```text
service/accueil exposed
NAME            ADDRESSTYPE   PORTS   ENDPOINTS    AGE
accueil-zbtbn   IPv4          8080    10.244.0.5   0s
```

The Service found the Pod: its address is in `ENDPOINTS`. So the lesson's
"selector that finds nothing" failure is not the cause. Yet query the
application:

```bash
kubectl exec outil -n essai-web -- wget -qO- -T 3 http://accueil:8080
```

```text
wget: can't connect to remote host (10.96.187.78): Connection refused
command terminated with exit code 1
```

`Connection refused`: the request does reach the Pod, but nothing listens on
the targeted port there. Read the two ports of the Service:

```bash
kubectl describe service accueil -n essai-web | grep -E "^(Port|TargetPort|Endpoints)"
```

```text
Port:                     <unset>  8080/TCP
TargetPort:               8080/TCP
Endpoints:                10.244.0.5:8080
```

Without `--target-port`, kubectl reuses the value of `--port`. The Service
therefore sends to port `8080` of the Pod, while nginx listens on `80`.
Recreate it with the right port, then save the page to a file, on the lab
machine:

```bash
kubectl delete service accueil -n essai-web
kubectl expose deployment accueil --port=8080 --target-port=80 -n essai-web
kubectl exec outil -n essai-web -- wget -qO- -T 3 http://accueil:8080 > ~/essai-reponse.html
head -4 ~/essai-reponse.html
```

```text title="Excerpt of the output"
service/accueil exposed
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
```

The `>` redirection is read by your shell, not by the Pod: the
`~/essai-reponse.html` file is written on the machine where you type the
command.

## 📚 Exercise 3: a Service with no Pod behind it

Scale the Deployment down to zero Pods, wait until the Pod is deleted, then
look at the Service:

```bash
kubectl scale deployment accueil --replicas=0 -n essai-web
kubectl wait --for=delete pod -l app=accueil -n essai-web --timeout=60s
kubectl get endpointslice -n essai-web -l kubernetes.io/service-name=accueil
kubectl exec outil -n essai-web -- wget -qO- -T 3 http://accueil:8080
```

```text
deployment.apps/accueil scaled
pod/accueil-654cbccb8f-w726j condition met
NAME            ADDRESSTYPE   PORTS     ENDPOINTS   AGE
accueil-8657t   IPv4          <unset>   <unset>     4s
wget: download timed out
command terminated with exit code 1
```

The Service still exists, with its address, but it has no endpoint any more.
Compare with exercise 2: a wrong port gives `Connection refused`, no Pod gives
`download timed out`, after the 3 seconds set by `-T 3`. The `wget` message
tells you where to look.

## 📚 Exercise 4: see which Pod each request goes to

Go back to two Pods, then send six requests to the Service:

```bash
kubectl scale deployment accueil --replicas=2 -n essai-web
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
for i in 1 2 3 4 5 6; do kubectl exec outil -n essai-web -- wget -qO /dev/null "http://accueil:8080"; done
```

```text
deployment.apps/accueil scaled
deployment.apps/accueil condition met
```

`kubectl logs deployment/accueil` only reads the log of one Pod. With
`-l app=accueil`, kubectl reads every Pod that carries this label, and
`--prefix` writes in front of each line the Pod it comes from:

```bash
kubectl logs -l app=accueil -n essai-web --prefix | grep GET
```

```text
[pod/accueil-654cbccb8f-sdswl/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:41 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-sdswl/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-sdswl/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-vvhdx/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:41 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-vvhdx/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
[pod/accueil-654cbccb8f-vvhdx/nginx] 10.244.0.6 - - [20/Nov/2026:07:07:42 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
```

Here, three requests per Pod. The Service picks a Pod at random for each
connection: on your side, the split may be four and two. Every request comes
from `10.244.0.6`, the address of the `outil` Pod. These are only the requests
of this exercise: the Pods were recreated in exercise 3, with an empty log.

## 📚 Exercise 5: move to a file, and read before applying

So far, you gave your orders one by one. The module challenge will ask you to
fix a Deployment in its file, then apply it with `kubectl apply -f`. Have
kubectl write a file: `--dry-run=client` prepares the object without sending
it to the cluster, and `-o yaml` prints it.

```bash
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web --dry-run=client -o yaml > ~/essai-accueil.yaml
grep -E "replicas|image:" ~/essai-accueil.yaml
```

```text
  replicas: 1
      - image: nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Before applying a file, ask what it would change. `kubectl diff` compares the
file with the object in the cluster, without changing anything:

```bash
kubectl diff -f ~/essai-accueil.yaml
echo "kubectl diff exit code: $?"
```

```text title="Excerpt of the output"
-  replicas: 2
+  replicas: 1
kubectl diff exit code: 1
```

The `-` lines show the cluster, the `+` lines what the object would become.
The generated file carries `replicas: 1`, the default value. Applying it would
therefore delete one of your two Pods. Exit code `1` signals a difference. Fix
the file for three Pods, read the difference again, then apply:

```bash
sed -i "s/replicas: 1/replicas: 3/" ~/essai-accueil.yaml
kubectl diff -f ~/essai-accueil.yaml
kubectl apply -f ~/essai-accueil.yaml
```

```text title="Excerpt of the output"
-  replicas: 2
+  replicas: 3
Warning: resource deployments/accueil is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. kubectl apply should only be used on resources created declaratively by either kubectl create --save-config or kubectl apply. The missing annotation will be patched automatically.
deployment.apps/accueil configured
```

`configured`: the object existed, and `apply` changed it. The warning is
normal the first time, as the lesson explains: the object was created by
`kubectl create`, and `apply` adds the annotation where it keeps the last
applied configuration. Run `kubectl diff` again:

```bash
kubectl diff -f ~/essai-accueil.yaml
echo "kubectl diff exit code: $?"
kubectl get deployment accueil -n essai-web
```

```text
kubectl diff exit code: 0
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
accueil   2/3     3            2           25s
```

No difference any more, and the exit code is `0`: the cluster matches the
file. `READY 2/3`: the third Pod is starting, it will be ready a few seconds
later.

## 🧹 Clean up

Delete what you created during the exercises: the scratch namespace and the
two files. Everything in the namespace goes with it: the Deployment, its Pods,
the `outil` Pod and the Service.

```bash
kubectl delete namespace essai-web
rm ~/essai-reponse.html ~/essai-accueil.yaml
```

```text
namespace "essai-web" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-premier-deploiement
dsoxlab check k8s-premier-deploiement
```

```text
╭─ Result: k8s-premier-deploiement ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: deploy, expose and scale the challenge's
application, then keep its answer in a file.

```bash
dsoxlab run k8s-premier-deploiement
dsoxlab challenge k8s-premier-deploiement
```
