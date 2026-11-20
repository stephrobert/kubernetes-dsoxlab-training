# Trace a Pod back to its Deployment

A **Deployment** does not create its Pods itself. It creates a **ReplicaSet**,
an object whose only job is to keep the right number of Pods, and it is the
ReplicaSet that creates the Pods. Each object keeps track of the one that
created it, its **owner**. The lesson follows this chain on a Deployment it
creates. This course starts from a Pod name alone, shows Pods that do not
come from a ReplicaSet, takes a Pod out of its ReplicaSet, then diagnoses a
ReplicaSet that cannot create its Pods.

You work in two scratch namespaces, `essai-rs` and `essai-quota`. The
challenge will ask you for the same kind of reading on other objects: you will
do it on your own, at the end.

Related page: [Kubernetes ReplicaSet: what a Deployment creates](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/replicasets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-lire-les-replicasets
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 and 20
November 2026.

## 📚 Exercise 1: go up from a Pod to its Deployment

Often you only know a Pod name, read in an alert or a log. Start from a
`coredns` Pod, the cluster's name service, and go up the chain of owners. The
`ownerReferences` field names the owner of an object; the `OWN` variable keeps
the path to print:

```bash
OWN='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
P=$(kubectl get pods -n kube-system -l k8s-app=kube-dns -o jsonpath='{.items[0].metadata.name}')
echo $P
kubectl get pod $P -n kube-system -o jsonpath="$OWN"
```

```text
coredns-559f6c778d-jwhr5
ReplicaSet/coredns-559f6c778d
```

The Pod belongs to a ReplicaSet. Go up one level, then one more:

```bash
kubectl get replicaset coredns-559f6c778d -n kube-system -o jsonpath="$OWN"
kubectl get deployment coredns -n kube-system -o jsonpath='{.metadata.ownerReferences}{"\n"}'
```

```text
Deployment/coredns
```

The ReplicaSet belongs to the `coredns` Deployment. The last command only
prints an empty line: the Deployment has no owner, it is the top of the
chain. The Pod's name already summed it up: `coredns-559f6c778d-jwhr5` is the
Deployment, then the ReplicaSet's fingerprint, then a random suffix.

## 📚 Exercise 2: see a Pod that has no ReplicaSet

Not every Pod comes from a ReplicaSet. Do the same reading on a `kube-proxy`
Pod and on the `etcd` Pod:

```bash
K=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy -o jsonpath='{.items[0].metadata.name}')
kubectl get pod $K -n kube-system -o jsonpath="$OWN"
E=$(kubectl get pods -n kube-system -l component=etcd -o jsonpath='{.items[0].metadata.name}')
kubectl get pod $E -n kube-system -o jsonpath="$OWN"
kubectl get replicaset -n kube-system
```

```text
DaemonSet/kube-proxy
Node/boutique-control-plane
NAME                 DESIRED   CURRENT   READY   AGE
coredns-559f6c778d   2         2         2       77m
```

`kube-proxy` belongs to a **DaemonSet**, an object that places one Pod on each
node, without a ReplicaSet. `etcd` is tied to the node itself: it is a Pod the
kubelet starts from a file placed on the node. The `kube-system` namespace
therefore holds a single ReplicaSet, the one of `coredns`. Going up from a Pod
does not always lead to a Deployment.

## 📚 Exercise 3: take a Pod out of its ReplicaSet

A ReplicaSet recognises its Pods by their **labels**, not by their name.
Create a Deployment of three Pods, and print their labels:

```bash
kubectl create namespace essai-rs
kubectl create deployment catalogue \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=3 -n essai-rs
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s
kubectl get pods -n essai-rs --show-labels
```

```text title="Excerpt of the output"
namespace/essai-rs created
deployment.apps/catalogue created
deployment "catalogue" successfully rolled out
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
catalogue-75867bdb5-5gv8j   1/1     Running   0          1s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-jd9c8   1/1     Running   0          1s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-xp9nv   1/1     Running   0          1s    app=catalogue,pod-template-hash=75867bdb5
```

Remove the `app` label from one of the Pods. `kubectl label` sets or removes
a label, and the final `-` means "remove"; the lesson on labels covers it
later:

```bash
X=$(kubectl get pods -n essai-rs -l app=catalogue -o jsonpath='{.items[0].metadata.name}')
kubectl label pod $X -n essai-rs app-
kubectl get pods -n essai-rs --show-labels
```

```text
pod/catalogue-75867bdb5-5gv8j unlabeled
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
catalogue-75867bdb5-5gv8j   1/1     Running   0          6s    pod-template-hash=75867bdb5
catalogue-75867bdb5-jd9c8   1/1     Running   0          6s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-kxt5g   1/1     Running   0          5s    app=catalogue,pod-template-hash=75867bdb5
catalogue-75867bdb5-xp9nv   1/1     Running   0          6s    app=catalogue,pod-template-hash=75867bdb5
```

Four Pods run now. The ReplicaSet no longer counts `5gv8j` among its own: it
only saw two, and it created a third one, `kxt5g`. The `5gv8j` Pod keeps
running. Read its owner:

```bash
kubectl get pod $X -n essai-rs -o jsonpath='{.metadata.ownerReferences}{"\n"}'
kubectl get replicaset -n essai-rs
```

```text

NAME                  DESIRED   CURRENT   READY   AGE
catalogue-75867bdb5   3         3         3       6s
```

Empty line: the Pod no longer has an owner. No controller will recreate it if
it falls, nor delete it. The ReplicaSet still counts three Pods, without it.

## 📚 Exercise 4: replace the Pods without changing the image

`kubectl rollout restart` has every Pod of a Deployment replaced, without
changing anything else. Run it, then look at the ReplicaSets:

```bash
kubectl rollout restart deployment/catalogue -n essai-rs
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s
kubectl get replicaset -n essai-rs -o custom-columns='NOM:.metadata.name,VOULUS:.spec.replicas,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision'
```

```text title="Excerpt of the output"
deployment.apps/catalogue restarted
deployment "catalogue" successfully rolled out
NOM                   VOULUS   REVISION
catalogue-75867bdb5   0        1
catalogue-c4bb56c49   3        2
```

A second ReplicaSet appeared, as for a new image, and the first one is kept at
zero. Yet the image did not change. Look at what `restart` changed in the Pod
template:

```bash
kubectl get deployment catalogue -n essai-rs -o jsonpath='{.spec.template.metadata.annotations}{"\n"}'
kubectl get pods -n essai-rs
```

```text
{"kubectl.kubernetes.io/restartedAt":"2026-11-20T08:19:47Z"}
NAME                        READY   STATUS        RESTARTS   AGE
catalogue-75867bdb5-5gv8j   1/1     Running       0          8s
catalogue-75867bdb5-jd9c8   1/1     Terminating   0          8s
catalogue-c4bb56c49-bztv4   1/1     Running       0          1s
catalogue-c4bb56c49-cxmcq   1/1     Running       0          2s
catalogue-c4bb56c49-jq6hd   1/1     Running       0          1s
```

`restart` puts a dated annotation in the Pod template. The template changes,
so its fingerprint changes, so the Deployment creates a ReplicaSet. The
`5gv8j` Pod from exercise 3 still runs: with no owner, it belongs to no
ReplicaSet, and the restart did not touch it. Delete this namespace, you no
longer need it:

```bash
kubectl delete namespace essai-rs
```

```text
namespace "essai-rs" deleted
```

## 📚 Exercise 5: diagnose a blocked ReplicaSet

A **quota** limits what a namespace is allowed to hold; the lesson on quotas,
much later in the course, covers it. Create a namespace limited to a single
Pod, then a Deployment that asks for two:

```bash
kubectl create namespace essai-quota
kubectl create quota plafond --hard=pods=1 -n essai-quota
kubectl create deployment borne \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=2 -n essai-quota
sleep 10
kubectl get deployment borne -n essai-quota
kubectl get replicaset -n essai-quota
```

```text
namespace/essai-quota created
resourcequota/plafond created
deployment.apps/borne created
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
borne   1/2     1            1           10s
NAME               DESIRED   CURRENT   READY   AGE
borne-6f65f67d68   2         1         1       10s
```

The ReplicaSet wants 2 Pods (`DESIRED`) but only has one (`CURRENT`). The
missing Pod does not exist, so there is no Pod to describe. Go up one level: it
is the ReplicaSet that tried to create it, and its events say why it failed:

```bash
kubectl describe replicaset -n essai-quota -l app=borne | sed -n '/^Events:/,$p'
```

```text title="Excerpt of the output"
Events:
  Type     Reason            Age   From                   Message
  ----     ------            ----  ----                   -------
  Normal   SuccessfulCreate  10s   replicaset-controller  Created pod: borne-6f65f67d68-rdj78
  Warning  FailedCreate      10s   replicaset-controller  Error creating: pods "borne-6f65f67d68-m7whr" is forbidden: exceeded quota: plafond, requested: pods=1, used: pods=1, limited: pods=1
  Warning  FailedCreate      10s   replicaset-controller  Error creating: pods "borne-6f65f67d68-ngtpf" is forbidden: exceeded quota: plafond, requested: pods=1, used: pods=1, limited: pods=1
```

`FailedCreate` gives the cause: the `plafond` quota is reached
(`used: pods=1, limited: pods=1`). The ReplicaSet tried again several times,
and the full list holds about ten identical lines.

## 📚 Exercise 6: remove the cause and watch the ReplicaSet try again

Raise the quota to three Pods, without touching the Deployment:

```bash
kubectl patch quota plafond -n essai-quota --type=merge -p '{"spec":{"hard":{"pods":"3"}}}'
kubectl get quota plafond -n essai-quota
kubectl wait --for=condition=Available deployment/borne -n essai-quota --timeout=180s
kubectl get deployment borne -n essai-quota
```

```text
resourcequota/plafond patched
NAME      REQUEST     LIMIT   AGE
plafond   pods: 1/3           10s
deployment.apps/borne condition met
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
borne   2/2     2            2           11s
```

You restarted nothing: the ReplicaSet tries again on its own as long as the
creation fails, and the second Pod showed up as soon as the quota allowed it.
Careful, it waits a little longer after each failure: on a ReplicaSet blocked
for a long time, recovery can take a minute or more.

## 🧹 Clean up

First delete what is left of the exercises: the `essai-quota` namespace. The
`essai-rs` namespace is already deleted.

```bash
kubectl delete namespace essai-quota
```

```text
namespace "essai-quota" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-lire-les-replicasets
dsoxlab check k8s-lire-les-replicasets
```

```text
╭─ Result: k8s-lire-les-replicasets ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests   │
╰────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: find the ReplicaSets of an updated
application, then diagnose and repair a Deployment that has no Pod.

```bash
dsoxlab run k8s-lire-les-replicasets
dsoxlab challenge k8s-lire-les-replicasets
```
