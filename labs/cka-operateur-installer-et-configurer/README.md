# Install an operator and configure what it runs

The lesson shows an operator that creates and maintains an application's
objects from a single resource. Every operator relies on one cluster
mechanism: each object it creates carries an owner, and the cluster acts on
it. This course has you work with that mechanism using the controllers
already built into Kubernetes, without an operator: read who owns what, give
an object an owner, delete without the children then have them adopted, take
a child out of its group, and delete in the foreground.

You work in a scratch namespace, `essai-proprio`, with a Deployment
`comptoir` ("counter", nginx) and a ConfigMap `fiche` ("card"). The challenge
is about the MongoDB operator and its objects: you will do it on your own, at
the end.

Related page: [Kubernetes operators](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/operators/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-operateur-installer-et-configurer
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and a Deployment with two replicas:

```bash
kubectl create namespace essai-proprio; kubectl create deployment comptoir --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=2 -n essai-proprio; kubectl rollout status deployment/comptoir -n essai-proprio --timeout=120s
```

```text
namespace/essai-proprio created
deployment.apps/comptoir created
Waiting for deployment "comptoir" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "comptoir" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "comptoir" rollout to finish: 1 of 2 updated replicas are available...
deployment "comptoir" successfully rolled out
```

## 🔗 Exercise 1: who owns what

Every object created by a controller carries its owner in the
`metadata.ownerReferences` field. Read it on the ReplicaSet, then on the Pods:

```bash
kubectl get replicaset -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} <- {.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name} controller={.metadata.ownerReferences[0].controller}{"\n"}{end}'; kubectl get pods -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} <- {.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'
```

```text
comptoir-c9b9dfdf7 <- Deployment/comptoir controller=true
comptoir-c9b9dfdf7-nssb2 <- ReplicaSet/comptoir-c9b9dfdf7
comptoir-c9b9dfdf7-pvwtk <- ReplicaSet/comptoir-c9b9dfdf7
```

The Deployment owns the ReplicaSet, which owns the Pods. `controller=true`
marks the owner that manages the object: an object has only one. This is
exactly what an operator does with what it creates: when the challenge asks
what it runs, the `ownerReferences` answer.

## 🏷️ Exercise 2: give an object an owner

An owner is named by its kind, its name and its UID, the unique identifier
the API gave it at creation. Create a ConfigMap owned by the Deployment:

```bash
UID_D=$(kubectl get deployment comptoir -n essai-proprio -o jsonpath='{.metadata.uid}'); cat <<YAML | kubectl apply -n essai-proprio -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: fiche
  ownerReferences:
    - apiVersion: apps/v1
      kind: Deployment
      name: comptoir
      uid: $UID_D
data:
  note: possédée par comptoir
YAML
kubectl get configmap fiche -n essai-proprio
```

```text
configmap/fiche created
NAME    DATA   AGE
fiche   1      0s
```

The API accepts the field as it is. The name alone is not enough: the UID is
what counts. A Deployment deleted then recreated under the same name will have
another UID, and will not be the owner of this ConfigMap.

## 👶 Exercise 3: delete without the children, then have them adopted

Delete the Deployment with `--cascade=orphan`: the objects it owns stay in
place.

```bash
kubectl delete deployment comptoir -n essai-proprio --cascade=orphan; sleep 5; kubectl get deployment,replicaset,pods,configmap -n essai-proprio
```

```text
deployment.apps "comptoir" deleted from essai-proprio namespace
NAME                                 DESIRED   CURRENT   READY   AGE
replicaset.apps/comptoir-c9b9dfdf7   2         2         2       6s

NAME                           READY   STATUS    RESTARTS   AGE
pod/comptoir-c9b9dfdf7-nssb2   1/1     Running   0          6s
pod/comptoir-c9b9dfdf7-pvwtk   1/1     Running   0          6s

NAME                         DATA   AGE
configmap/fiche              1      5s
configmap/kube-root-ca.crt   1      6s
```

The ReplicaSet, the Pods and the ConfigMap are still there. The ReplicaSet no
longer has an owner (`propriétaires` means "owners"):

```bash
kubectl get replicaset -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} propriétaires={.metadata.ownerReferences}{"\n"}{end}'
```

```text
comptoir-c9b9dfdf7 propriétaires=
```

Recreate the Deployment identically:

```bash
kubectl create deployment comptoir --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=2 -n essai-proprio; sleep 5; kubectl get replicaset -n essai-proprio -o jsonpath='{range .items[*]}{.metadata.name} <- {.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'; kubectl get pods -n essai-proprio
```

```text
deployment.apps/comptoir created
comptoir-c9b9dfdf7 <- Deployment/comptoir
NAME                       READY   STATUS    RESTARTS   AGE
comptoir-c9b9dfdf7-nssb2   1/1     Running   0          12s
comptoir-c9b9dfdf7-pvwtk   1/1     Running   0          12s
```

The new Deployment adopted the old ReplicaSet, whose Pods did not restart
(their age keeps going). It recognised it by its selector and its identical
template. This is how you replace an object you cannot modify, without
cutting the application off.

## 📄 Exercise 4: the card lost its owner

Look at the `fiche` ConfigMap:

```bash
kubectl get configmap fiche -n essai-proprio -o jsonpath='{.metadata.name} propriétaires={.metadata.ownerReferences}{"\n"}'
```

```text
fiche propriétaires=
```

It no longer has an owner. Deleting with `--cascade=orphan` removed the
reference from every owned object, the ConfigMap included. And the adoption
in exercise 3 only concerns ReplicaSets: the new Deployment does not take a
ConfigMap back.

## 🚪 Exercise 5: a child that leaves the selector

Change the `app` label of one of the Pods, so that it no longer matches the
ReplicaSet's selector:

```bash
P=$(kubectl get pods -n essai-proprio -l app=comptoir -o jsonpath='{.items[0].metadata.name}'); kubectl label pod $P -n essai-proprio app=rayon --overwrite; sleep 5; kubectl get pods -n essai-proprio -L app; kubectl get pod $P -n essai-proprio -o jsonpath='propriétaires : {.metadata.ownerReferences}{"\n"}'
```

```text
pod/comptoir-c9b9dfdf7-nssb2 labeled
NAME                       READY   STATUS    RESTARTS   AGE   APP
comptoir-c9b9dfdf7-jv825   1/1     Running   0          5s    comptoir
comptoir-c9b9dfdf7-nssb2   1/1     Running   0          17s   rayon
comptoir-c9b9dfdf7-pvwtk   1/1     Running   0          17s   comptoir
propriétaires : 
```

The ReplicaSet released that Pod (it has no owner any more) and created
another one to get back to two. The released Pod keeps running, outside any
control. This is a known troubleshooting move: you take a sick Pod out of the
group to examine it, without reducing the number of replicas.

## 🗑️ Exercise 6: delete in the foreground

Give the ConfigMap back to the Deployment, with its new UID:

```bash
UID_D=$(kubectl get deployment comptoir -n essai-proprio -o jsonpath='{.metadata.uid}'); kubectl patch configmap fiche -n essai-proprio --type merge -p "{\"metadata\":{\"ownerReferences\":[{\"apiVersion\":\"apps/v1\",\"kind\":\"Deployment\",\"name\":\"comptoir\",\"uid\":\"$UID_D\"}]}}"; kubectl get configmap fiche -n essai-proprio -o jsonpath='{.metadata.ownerReferences[0].name}{"\n"}'
```

```text
configmap/fiche patched
comptoir
```

Delete the Deployment with `--cascade=foreground`, without waiting for the
end, then look at it before and after the cluster's garbage collector does its
work:

```bash
kubectl delete deployment comptoir -n essai-proprio --cascade=foreground --wait=false; kubectl get deployment comptoir -n essai-proprio -o jsonpath='finalizers={.metadata.finalizers} suppression={.metadata.deletionTimestamp}{"\n"}'; sleep 15; kubectl get deployment,replicaset,pods,configmap -n essai-proprio
```

```text
deployment.apps "comptoir" deleted from essai-proprio namespace
finalizers=["foregroundDeletion"] suppression=2026-11-21T00:50:00Z
NAME                           READY   STATUS    RESTARTS   AGE
pod/comptoir-c9b9dfdf7-nssb2   1/1     Running   0          32s

NAME                         DATA   AGE
configmap/kube-root-ca.crt   1      32s
```

Right after the command, the Deployment still exists, marked for deletion,
with the `foregroundDeletion` finalizer: it waits for its children to be
deleted before it goes. Fifteen seconds later, the ReplicaSet, its Pods and
the ConfigMap are gone. Only the Pod released in exercise 5 remains: it had
no owner any more. With an operator, the same mechanism removes everything it
created when you delete its resource.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-proprio
```

```text
namespace "essai-proprio" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-operateur-installer-et-configurer
dsoxlab check cka-operateur-installer-et-configurer
```

```text
╭─ Result: cka-operateur-installer-et-configurer ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests                │
╰─────────────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: install the MongoDB operator, have it
create a database, and tune what it runs.

```bash
dsoxlab run cka-operateur-installer-et-configurer
dsoxlab challenge cka-operateur-installer-et-configurer
```
