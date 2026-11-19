# Trace a Pod back to its Deployment

A **Deployment** does not create its Pods itself. It creates a **ReplicaSet**,
an object whose only job is to keep the right number of Pods, and it is the
ReplicaSet that creates the Pods. Each object keeps track of the one that
created it, its **owner**. In this course, you follow this chain, you see what
becomes of a ReplicaSet after an update, and you diagnose a ReplicaSet that
cannot create its Pods.

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

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: create a Deployment and see its ReplicaSet

Create the scratch namespace, then write the file of a Deployment `catalogue`
of three Pods:

```bash
kubectl create namespace essai-rs
cat > ~/catalogue.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: essai-rs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
EOF
```

Create it, wait for it to be ready, then look at the ReplicaSets:

```bash
kubectl apply -f ~/catalogue.yaml
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s
kubectl get replicaset -n essai-rs -l app=catalogue
```

```text
deployment.apps/catalogue created
Waiting for deployment "catalogue" rollout to finish: 0 out of 3 new replicas have been updated...
Waiting for deployment "catalogue" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "catalogue" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "catalogue" rollout to finish: 2 of 3 updated replicas are available...
deployment "catalogue" successfully rolled out
NAME                  DESIRED   CURRENT   READY   AGE
catalogue-75867bdb5   3         3         3       1s
```

A ReplicaSet showed up. Its name is the Deployment's, followed by a
**fingerprint** (`75867bdb5`) computed from the description of the Pods.
`DESIRED`, `CURRENT` and `READY` say how many Pods it wants, has, and has ready.

## 📚 Exercise 2: go up from owner to owner

An object's `ownerReferences` field says who created it. Read it on the
ReplicaSet, then on a Pod:

```bash
kubectl get replicaset -n essai-rs -l app=catalogue \
  -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}/{.items[0].metadata.ownerReferences[0].name}{"\n"}'
kubectl get pods -n essai-rs -l app=catalogue \
  -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}/{.items[0].metadata.ownerReferences[0].name}{"\n"}'
```

```text
Deployment/catalogue
ReplicaSet/catalogue-75867bdb5
```

The chain is complete: the Deployment owns the ReplicaSet, which owns the
Pods. Kubernetes uses it to delete the children when you delete the parent.

## 📚 Exercise 3: update and see a second ReplicaSet

Change the Deployment's image to the next nginx version:

```bash
kubectl set image deployment/catalogue \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-rs
kubectl rollout status deployment/catalogue -n essai-rs --timeout=120s | tail -1
```

```text
deployment.apps/catalogue image updated
deployment "catalogue" successfully rolled out
```

Now look at the ReplicaSets, with the useful columns:

```bash
kubectl get replicaset -n essai-rs -l app=catalogue \
  -o custom-columns=NOM:.metadata.name,VOULUS:.spec.replicas,PRETS:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image
```

```text
NOM                    VOULUS   PRETS    IMAGE
catalogue-5f44879b68   3        3        nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
catalogue-75867bdb5    0        <none>   nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

There are two now. The new one carries the three Pods, with the new image. The
old one is kept, but at **zero** Pods: it is used to go back without recreating
anything. To know which one carries the Pods today, look at the `VOULUS`
(wanted) column.

Each ReplicaSet recognises its Pods thanks to a label that holds its
fingerprint:

```bash
kubectl get replicaset -n essai-rs -l app=catalogue \
  -o custom-columns=NOM:.metadata.name,SELECTEUR:.spec.selector.matchLabels
```

```text
NOM                    SELECTEUR
catalogue-5f44879b68   map[app:catalogue pod-template-hash:5f44879b68]
catalogue-75867bdb5    map[app:catalogue pod-template-hash:75867bdb5]
```

The `pod-template-hash` label differs for each: it is what keeps the Pods of
the two versions apart.

## 📚 Exercise 4: watch a ReplicaSet adopt a Pod

A ReplicaSet keeps no list of its Pods. It counts the Pods that carry its
labels and have no owner yet. First create a lone Pod, with the `app=isole`
label:

```bash
kubectl run isole --labels=app=isole \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-rs
kubectl wait --for=condition=Ready pod/isole -n essai-rs --timeout=90s
```

```text
pod/isole created
pod/isole condition met
```

Then create a ReplicaSet that asks for three Pods with that same label:

```bash
cat > ~/isole-rs.yaml <<'EOF'
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: isole-rs
  namespace: essai-rs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: isole
  template:
    metadata:
      labels:
        app: isole
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
EOF
kubectl apply -f ~/isole-rs.yaml
kubectl wait --for=jsonpath='{.status.readyReplicas}'=3 replicaset/isole-rs -n essai-rs --timeout=90s
kubectl get pods -n essai-rs -l app=isole
```

```text
replicaset.apps/isole-rs created
replicaset.apps/isole-rs condition met
NAME             READY   STATUS    RESTARTS   AGE
isole            1/1     Running   0          1s
isole-rs-49gdz   1/1     Running   0          0s
isole-rs-4rhvs   1/1     Running   0          0s
```

Three Pods, but the ReplicaSet only created two. Its events and the owner of
the `isole` Pod confirm it:

```bash
kubectl describe replicaset isole-rs -n essai-rs | sed -n '/^Events:/,$p'
kubectl get pod isole -n essai-rs \
  -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
```

```text
Events:
  Type    Reason            Age   From                   Message
  ----    ------            ----  ----                   -------
  Normal  SuccessfulCreate  0s    replicaset-controller  Created pod: isole-rs-49gdz
  Normal  SuccessfulCreate  0s    replicaset-controller  Created pod: isole-rs-4rhvs
ReplicaSet/isole-rs
```

The `isole` Pod already existed and carried the right label: the ReplicaSet
took it over, and it is now its owner. Remember: two controllers must never
look for the same labels.

## 📚 Exercise 5: diagnose a blocked ReplicaSet

A **quota** limits what a namespace is allowed to hold. Create a namespace
limited to a single Pod, then a Deployment that asks for two:

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

`FailedCreate` gives the cause: the `plafond` quota is reached (`used: pods=1,
limited: pods=1`). The ReplicaSet tried again several times, and the full list
holds about ten identical lines.

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

Delete both scratch namespaces and both files:

```bash
kubectl delete namespace essai-rs essai-quota
rm ~/catalogue.yaml ~/isole-rs.yaml
```

```text
namespace "essai-rs" deleted
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
