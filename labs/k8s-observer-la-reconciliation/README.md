# Watch the control plane reconcile

The **control plane** is the part of the cluster that decides: it keeps the
state you asked for and makes the cluster match it. Its components run as Pods
on the `control-plane` node:

- the **API server** receives every request;
- **etcd** is the database that keeps the cluster's state;
- the **scheduler** picks a node for each Pod;
- the **controller manager** runs the **controllers**.

A controller keeps comparing what you asked for with what exists, and fixes
the gap. This is called **reconciliation**. In this course, you cause gaps and
watch the controllers fix them.

You work in a scratch namespace, `essai-boucle`, with a Deployment `boucle`.
The challenge will ask you to repeat the observation on another application:
you will do it on your own, at the end.

Related page: [Kubernetes control plane](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/control-plane/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-observer-la-reconciliation
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`architecture` is running there, with one control plane and three workers, and
your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: find the control plane components

On kind, the control plane components are Pods of the `kube-system`
namespace, with the `tier=control-plane` label:

```bash
kubectl get pods -n kube-system -l tier=control-plane
```

```text
NAME                                                 READY   STATUS    RESTARTS   AGE
etcd-architecture-control-plane                      1/1     Running   0          5m53s
kube-apiserver-architecture-control-plane            1/1     Running   0          5m53s
kube-controller-manager-architecture-control-plane   1/1     Running   0          5m53s
kube-scheduler-architecture-control-plane            1/1     Running   0          5m53s
```

The four components run. These Pods are special: the node's kubelet starts
them itself, from files placed on the node, without going through the
scheduler. Check it on the scheduler's one:

```bash
kubectl describe pod -n kube-system kube-scheduler-architecture-control-plane \
  | grep -E 'config.source|Controlled By'
```

```text
                      kubernetes.io/config.source: file
Controlled By:  Node/architecture-control-plane
```

`config.source: file`: the Pod comes from a file on the node. `Controlled By`
names the node, not a ReplicaSet.

## 📚 Exercise 2: ask the API server whether it is healthy

```bash
kubectl get --raw /readyz; echo
kubectl get --raw '/readyz?verbose' | grep -E 'etcd |passed'
```

```text
ok
[+]etcd ok
readyz check passed
```

`ok`: the API server is ready to answer. With `?verbose`, it details its
checks, including etcd's: `[+]etcd ok` shows it does reach the database.

## 📚 Exercise 3: create a Pod no node accepts

The scheduler starts no container: it only picks a node. Check it with a Pod
that requires a `disque: ssd` label, which no node carries. Create the scratch
namespace, then the Pod's file:

```bash
kubectl create namespace essai-boucle
cat > ~/exige-ssd.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: exige-ssd
  namespace: essai-boucle
spec:
  nodeSelector:
    disque: ssd
  containers:
    - name: web
      image: nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
EOF
```

Create the Pod, wait a few seconds, then look at it:

```bash
kubectl apply -f ~/exige-ssd.yaml
sleep 5
kubectl get pod exige-ssd -n essai-boucle
kubectl describe pod exige-ssd -n essai-boucle | sed -n '/^Events:/,$p'
```

```text
pod/exige-ssd created
NAME        READY   STATUS    RESTARTS   AGE
exige-ssd   0/1     Pending   0          5s
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  5s    default-scheduler  0/4 nodes are available: 1 node(s) had untolerated taint(s), 3 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 4 Preemption is not helpful for scheduling.
```

The Pod stays `Pending`: the scheduler found no node, so no container started.
The message says why, node by node: the control plane is ruled out by its mark
(`taint`), the three workers because they lack the `disque: ssd` label. In
front of a `Pending` Pod, read these events first. Then delete this scratch
Pod:

```bash
kubectl delete pod exige-ssd -n essai-boucle
rm ~/exige-ssd.yaml
```

```text
pod "exige-ssd" deleted from essai-boucle namespace
```

## 📚 Exercise 4: change the number of Pods asked for

Create a Deployment of three Pods, wait for it to be ready, then ask for five:

```bash
kubectl create deployment boucle \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=3 -n essai-boucle
kubectl wait --for=condition=Available deployment/boucle -n essai-boucle --timeout=180s
kubectl scale deployment boucle --replicas=5 -n essai-boucle
kubectl get pods -n essai-boucle
```

```text
deployment.apps/boucle created
deployment.apps/boucle condition met
deployment.apps/boucle scaled
NAME                      READY   STATUS              RESTARTS   AGE
boucle-5f64888d87-4dss7   1/1     Running             0          1s
boucle-5f64888d87-8hnwr   0/1     ContainerCreating   0          0s
boucle-5f64888d87-h2sz9   1/1     Running             0          1s
boucle-5f64888d87-kqvs7   1/1     Running             0          1s
boucle-5f64888d87-r8x4t   0/1     Pending             0          0s
```

You changed a single number, and two Pods showed up (age `0s`). Go back to
three, then read the ReplicaSet's events:

```bash
kubectl scale deployment boucle --replicas=3 -n essai-boucle
sleep 5
RS=$(kubectl get rs -n essai-boucle -o jsonpath='{.items[0].metadata.name}')
kubectl describe rs $RS -n essai-boucle | sed -n '/^Events:/,$p'
```

```text
deployment.apps/boucle scaled
Events:
  Type    Reason            Age   From                   Message
  ----    ------            ----  ----                   -------
  Normal  SuccessfulCreate  6s    replicaset-controller  Created pod: boucle-5f64888d87-kqvs7
  Normal  SuccessfulCreate  6s    replicaset-controller  Created pod: boucle-5f64888d87-4dss7
  Normal  SuccessfulCreate  6s    replicaset-controller  Created pod: boucle-5f64888d87-h2sz9
  Normal  SuccessfulCreate  5s    replicaset-controller  Created pod: boucle-5f64888d87-8hnwr
  Normal  SuccessfulCreate  5s    replicaset-controller  Created pod: boucle-5f64888d87-r8x4t
  Normal  SuccessfulDelete  5s    replicaset-controller  Deleted pod: boucle-5f64888d87-r8x4t
  Normal  SuccessfulDelete  5s    replicaset-controller  Deleted pod: boucle-5f64888d87-8hnwr
```

Read in order. The first three `SuccessfulCreate`: the creation of the
Deployment. The next two: the move to five, the controller saw 3 Pods for 5
asked and created 2. The two `SuccessfulDelete`: the move back to three, it saw
5 Pods for 3 asked and deleted 2. The same controller, `replicaset-controller`,
did all that work.

## 📚 Exercise 5: delete the ReplicaSet and watch it come back

The same loop exists one level up. Delete the ReplicaSet itself, and look right
away at what exists:

```bash
RS=$(kubectl get rs -n essai-boucle -o jsonpath='{.items[0].metadata.name}')
kubectl delete rs $RS -n essai-boucle
kubectl get rs,pods -n essai-boucle
```

```text
replicaset.apps "boucle-5f64888d87" deleted from essai-boucle namespace
NAME                                DESIRED   CURRENT   READY   AGE
replicaset.apps/boucle-5f64888d87   3         3         0       0s

NAME                          READY   STATUS              RESTARTS   AGE
pod/boucle-5f64888d87-4dss7   1/1     Terminating         0          6s
pod/boucle-5f64888d87-4thmb   0/1     ContainerCreating   0          0s
pod/boucle-5f64888d87-h2sz9   1/1     Terminating         0          6s
pod/boucle-5f64888d87-kqvs7   1/1     Terminating         0          6s
pod/boucle-5f64888d87-srzb7   0/1     Pending             0          0s
pod/boucle-5f64888d87-w47sh   0/1     Pending             0          0s
```

Two things happen at once. The three old Pods are `Terminating`: they go away
with their ReplicaSet. But a ReplicaSet already exists again (age `0s`), with
three new Pods. It has the same name, because this name is computed from the
description of the Pods, which did not change. Fifteen seconds later,
everything is back:

```bash
sleep 15
kubectl get rs,pods -n essai-boucle
```

```text
NAME                                DESIRED   CURRENT   READY   AGE
replicaset.apps/boucle-5f64888d87   3         3         3       15s

NAME                          READY   STATUS    RESTARTS   AGE
pod/boucle-5f64888d87-4thmb   1/1     Running   0          15s
pod/boucle-5f64888d87-srzb7   1/1     Running   0          15s
pod/boucle-5f64888d87-w47sh   1/1     Running   0          15s
```

Who recreated the ReplicaSet? The Deployment's events say:

```bash
kubectl describe deployment boucle -n essai-boucle | sed -n '/^Events:/,$p'
```

```text
Events:
  Type    Reason             Age                From                   Message
  ----    ------             ----               ----                   -------
  Normal  ScalingReplicaSet  20s                deployment-controller  Scaled up replica set boucle-5f64888d87 from 3 to 5
  Normal  ScalingReplicaSet  20s                deployment-controller  Scaled down replica set boucle-5f64888d87 from 5 to 3
  Normal  ScalingReplicaSet  15s (x2 over 21s)  deployment-controller  Scaled up replica set boucle-5f64888d87 from 0 to 3
```

`deployment-controller` saw a ReplicaSet was missing, and recreated it with 3
Pods. `(x2 over 21s)`: it has done it twice already, when the Deployment was
created and after the deletion.

## 🧹 Clean up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-boucle
```

```text
namespace "essai-boucle" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-observer-la-reconciliation
dsoxlab check k8s-observer-la-reconciliation
```

```text
╭─ Result: k8s-observer-la-reconciliation ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests         │
╰──────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: delete a Pod then the ReplicaSet of the
challenge's application, and record which controller recreated each.

```bash
dsoxlab run k8s-observer-la-reconciliation
dsoxlab challenge k8s-observer-la-reconciliation
```
