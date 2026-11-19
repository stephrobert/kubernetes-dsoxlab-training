# Deploy, expose and scale a first application

This course has you deploy your first application in Kubernetes, move by move,
as in the lesson: create a namespace, start the application, make it
reachable, check that it answers, then start one more copy of it.

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

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: create a namespace

Create the `essai-web` namespace, then check that it exists:

```bash
kubectl create namespace essai-web
kubectl get namespace essai-web
```

```text
namespace/essai-web created
NAME        STATUS   AGE
essai-web   Active   0s
```

`Active`: the namespace is ready. Every following command carries the
`-n essai-web` option. Without it, your objects would go to the `default`
namespace.

## 📚 Exercise 2: start the application with a Deployment

Create a Deployment `accueil` that runs the nginx web server. The image is
given with its digest (`@sha256:...`): you are sure to get exactly the one of
the lesson.

```bash
kubectl create deployment accueil \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-web
```

```text
deployment.apps/accueil created
```

Wait for the application to be available, then look at the Deployment:

```bash
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
kubectl get deployment accueil -n essai-web
```

```text
deployment.apps/accueil condition met
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
accueil   1/1     1            1           0s
```

The `READY` column shows `1/1`: one Pod asked for, one Pod ready.

The Deployment did not create the Pod itself. It created a **ReplicaSet**,
which created the Pod. See both:

```bash
kubectl get replicasets -n essai-web
kubectl get pods -n essai-web
```

```text
NAME                 DESIRED   CURRENT   READY   AGE
accueil-654cbccb8f   1         1         1       0s
NAME                       READY   STATUS    RESTARTS   AGE
accueil-654cbccb8f-stcjv   1/1     Running   0          0s
```

The Pod's name starts with the ReplicaSet's, which starts with the
Deployment's. The end of the name is random: yours will differ.

## 📚 Exercise 3: make the application reachable with a Service

A Pod can disappear and come back with another address. To reach it in a
stable way, you create a Service. This one listens on port `8080` and forwards
to port `80`, nginx's:

```bash
kubectl expose deployment accueil --port=8080 --target-port=80 -n essai-web
kubectl get service accueil -n essai-web
```

```text
service/accueil exposed
NAME      TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
accueil   ClusterIP   10.96.209.14   <none>        8080/TCP   0s
```

The `ClusterIP` type means the Service can only be reached from inside the
cluster. Its address (`CLUSTER-IP`) will differ on your side.

## 📚 Exercise 4: see how the Service finds the Pods

The Service does not know the Pods by name. It finds them thanks to a
**label** set on them. Show the Pod's labels:

```bash
kubectl get pods -n essai-web --show-labels
```

```text
NAME                       READY   STATUS    RESTARTS   AGE   LABELS
accueil-654cbccb8f-stcjv   1/1     Running   0          1s    app=accueil,pod-template-hash=654cbccb8f
```

The Pod carries the `app=accueil` label, set automatically from the
Deployment's name. Now look at what the Service looks for:

```bash
kubectl describe service accueil -n essai-web | grep -E "^(Selector|Port|TargetPort|Endpoints)"
```

```text
Selector:                 app=accueil
Port:                     <unset>  8080/TCP
TargetPort:               80/TCP
Endpoints:                10.244.0.9:80
```

`Selector` says which label the Service looks for: `app=accueil`, the Pod's.
`Endpoints` gives the address of the Pod it found.

Now create a Service that finds nothing, to see what the failure looks like:

```bash
kubectl create service clusterip vide --tcp=80:80 -n essai-web
kubectl describe service vide -n essai-web | grep -E "^(Selector|Endpoints)"
kubectl get endpointslice -n essai-web
```

```text
service/vide created
Selector:                 app=vide
Endpoints:
NAME            ADDRESSTYPE   PORTS     ENDPOINTS    AGE
accueil-qnnz4   IPv4          80        10.244.0.9   1s
vide-ccv5r      IPv4          <unset>   <unset>      0s
```

The `vide` Service looks for the `app=vide` label, which no Pod carries: its
`Endpoints` line is empty. Yet no error shows, neither at creation nor after.
Keep this reflex: when a Service does not answer, look at its endpoints first.

## 📚 Exercise 5: query the application from a Pod

A Service's name, `accueil`, only exists inside the cluster. Start a temporary
Pod with the busybox image, which holds the `wget` command, and ask for the
page:

```bash
kubectl run client \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  --rm -i --restart=Never -n essai-web -- wget -qO- http://accueil:8080
```

```text title="Excerpt of the output"
All commands and output from this session will be recorded in container logs, including credentials and sensitive information passed through the command prompt.
If you don't see a command prompt, try pressing enter.
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
pod "client" deleted from essai-web namespace
```

The first two lines are kubectl messages, not an error. Then comes nginx's
welcome page: the application answers. The `--rm` option deletes the `client`
Pod as soon as it is done, hence the last line.

## 📚 Exercise 6: start one more copy

Ask for two Pods instead of one, then wait for them to be ready:

```bash
kubectl scale deployment accueil --replicas=2 -n essai-web
kubectl wait --for=condition=Available deployment/accueil -n essai-web --timeout=120s
kubectl get pods -n essai-web -l app=accueil
```

```text
deployment.apps/accueil scaled
deployment.apps/accueil condition met
NAME                       READY   STATUS    RESTARTS   AGE
accueil-654cbccb8f-stcjv   1/1     Running   0          6s
accueil-654cbccb8f-t8j4n   1/1     Running   0          0s
```

A second Pod showed up. The `-l app=accueil` option only lists the Pods that
carry this label. The Service found the new Pod on its own:

```bash
kubectl get endpointslice -n essai-web -l kubernetes.io/service-name=accueil
```

```text
NAME            ADDRESSTYPE   PORTS   ENDPOINTS                AGE
accueil-qnnz4   IPv4          80      10.244.0.9,10.244.0.12   6s
```

Two addresses now: the Service shares requests between the two Pods, without
you changing anything.

## 📚 Exercise 7: follow what the application does

Read the last lines of the application's log:

```bash
kubectl logs deployment/accueil -n essai-web --tail=3
```

```text
Found 2 pods, using pod/accueil-654cbccb8f-stcjv
2026/11/19 10:45:23 [notice] 1#1: start worker process 37
10.244.0.10 - - [19/Nov/2026:10:45:25 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
10.244.0.11 - - [19/Nov/2026:10:45:27 +0000] "GET / HTTP/1.1" 200 896 "-" "Wget" "-"
```

The log always comes from one Pod: kubectl picked one of the two. You can see
the `GET /` requests made by `wget` in exercise 5, with code `200` (success).

Finally, look at what Kubernetes did, in order:

```bash
kubectl get events -n essai-web --sort-by=.lastTimestamp | tail -6
```

```text title="Excerpt of the output"
1s          Normal   ScalingReplicaSet   deployment/accueil              Scaled up replica set accueil-654cbccb8f from 1 to 2
1s          Normal   SuccessfulCreate    replicaset/accueil-654cbccb8f   Created pod: accueil-654cbccb8f-t8j4n
1s          Normal   Scheduled           pod/accueil-654cbccb8f-t8j4n    Successfully assigned essai-web/accueil-654cbccb8f-t8j4n to boutique-control-plane
1s          Normal   Started             pod/accueil-654cbccb8f-t8j4n    Container started
```

You read the chain of exercise 6: the Deployment asks the ReplicaSet for one
more Pod, the ReplicaSet creates it, then the Pod is placed on a node and
starts.

## 🧹 Clean up

Delete the scratch namespace. Everything in it goes with it: the Deployment,
its Pods and both Services.

```bash
kubectl delete namespace essai-web
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
