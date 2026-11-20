# Read what a worker Node declares

A **node** (Node) is a machine of the cluster. On each node, a program, the
**kubelet**, runs the Pods and keeps writing to the cluster what the machine
offers and how it is doing. The lesson shows how to read this information. In
this course, you cause changes on a node, then you read again what it
declares: a stopped kubelet, a node that comes back, a deleted system Pod.

You work on the `architecture-worker3` node. The challenge will ask you for
the sheet of another node: you will fill it on your own, at the end.

Related page: [How Kubernetes worker nodes work](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-lire-un-node
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`architecture` runs there, with one control plane and three workers, and your
kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: see what sets two nodes apart

On this cluster, the nodes are containers of the same machine: many of their
values are identical. Compare two workers on three lines of their sheet:

```bash
kubectl describe node architecture-worker | grep -E 'InternalIP|PodCIDR:|Machine ID'
kubectl describe node architecture-worker3 | grep -E 'InternalIP|PodCIDR:|Machine ID'
```

```text
  InternalIP:  172.18.0.7
  Machine ID:                 f524842260574d1fbf3b8ff528d7412d
PodCIDR:                      10.244.1.0/24
  InternalIP:  172.18.0.4
  Machine ID:                 6313db26e58b44398528deda41404384
PodCIDR:                      10.244.4.0/24
```

These three values belong to each node:

- `InternalIP` is the address of the node on the machines' network;
- `PodCIDR` is the address range where the Pods of this node get theirs: a Pod
  of `architecture-worker3` will get an address in `10.244.4.x`;
- `Machine ID` is the identifier of the machine, drawn at random when it is
  created.

They also change when the cluster is recreated: on your side, they will be
different. Other lines, on the contrary, are the same everywhere:

```bash
kubectl describe node architecture-worker3 | grep -E 'Kubelet Version|Container Runtime Version|^  memory'
```

```text
  memory:             4009788Ki
  memory:             4009788Ki
  Container Runtime Version:  containerd://2.3.4
  Kubelet Version:            v1.37.0
  memory             50Mi (1%)  0 (0%)
```

The first two `memory` lines come from `Capacity` and `Allocatable`, the last
one from `Allocated resources`: the memory already reserved by the Pods of the
node. Kubelet version, runtime and memory are the same on the four nodes of
this cluster.

## 📚 Exercise 2: place a witness Pod and read its tolerations

Create a scratch namespace and a Deployment of four Pods, to get at least one
on `architecture-worker3`:

```bash
kubectl create namespace essai-noeud
kubectl create deployment temoin \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=4 -n essai-noeud
kubectl wait --for=condition=Available deployment/temoin -n essai-noeud --timeout=180s
kubectl get pods -n essai-noeud -o wide --field-selector spec.nodeName=architecture-worker3
```

```text
namespace/essai-noeud created
deployment.apps/temoin created
deployment.apps/temoin condition met
NAME                      READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE   READINESS GATES
temoin-556cf4ff8c-8w9th   1/1     Running   0          1s    10.244.4.12   architecture-worker3   <none>           <none>
```

The `--field-selector spec.nodeName=...` option keeps only the Pods of that
node. Its address, `10.244.4.12`, is indeed in the node's `PodCIDR`.
Kubernetes added two **tolerations** to this Pod, rules that say how long it
stays on a node in trouble:

```bash
POD=$(kubectl get pods -n essai-noeud --field-selector spec.nodeName=architecture-worker3 -o jsonpath='{.items[0].metadata.name}')
kubectl describe pod $POD -n essai-noeud | sed -n '/^Tolerations:/,/^Events:/p'
```

```text
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
```

If the node is no longer ready (`not-ready`) or no longer reachable
(`unreachable`), this Pod stays there for 300 more seconds, then it is removed
from it. Keep this number for the next exercise.

## 📚 Exercise 3: stop the kubelet of a node

About every ten seconds, the kubelet renews a **lease** (Lease) named after its
node: it is its heartbeat. Read the time of the last renewal, then stop the
kubelet of `architecture-worker3`. On kind, the node is a Docker container:
`docker exec` runs a command inside it.

```bash
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
docker exec architecture-worker3 systemctl stop kubelet
docker exec architecture-worker3 systemctl is-active kubelet
```

```text
2026-11-20T07:41:39.949102Z
inactive
```

Wait about fifteen seconds, then read the lease again:

```bash
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
date -u +%H:%M:%S
```

```text
2026-11-20T07:41:39.949102Z
07:41:56
```

The time of the lease did not move, while the clock moved on by 17 seconds:
nobody renews it any more. Wait one more minute, then look at the nodes and at
the sheet of `architecture-worker3`:

```bash
sleep 60
kubectl get nodes
kubectl describe node architecture-worker3 | grep -E '^Taints|unreachable|^  Ready'
```

```text
NAME                         STATUS     ROLES           AGE   VERSION
architecture-control-plane   Ready      control-plane   14m   v1.37.0
architecture-worker          Ready      <none>          14m   v1.37.0
architecture-worker2         Ready      <none>          14m   v1.37.0
architecture-worker3         NotReady   <none>          14m   v1.37.0
Taints:             node.kubernetes.io/unreachable:NoExecute
                    node.kubernetes.io/unreachable:NoSchedule
  Ready            Unknown   Fri, 20 Nov 2026 07:41:09 +0000   Fri, 20 Nov 2026 07:42:33 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
```

On this machine, the node became `NotReady` after about one minute. The
`Ready` condition is `Unknown`: the cluster does not know whether the node is
broken, it only knows the kubelet no longer reports. It set two `unreachable`
**taints**:

- `NoSchedule`: no new Pod will be placed on this node;
- `NoExecute`: the Pods already there will be removed from it, after the delay
  of their toleration, that is 300 seconds for your witness Pod.

Look at this Pod:

```bash
kubectl get pods -n essai-noeud -o wide --field-selector spec.nodeName=architecture-worker3
```

```text
NAME                      READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE   READINESS GATES
temoin-556cf4ff8c-8w9th   1/1     Running   0          57s   10.244.4.12   architecture-worker3   <none>           <none>
```

It still shows `Running`. It is the last thing the kubelet told the cluster,
before it stopped: the cluster knows nothing more. The 300 seconds of its
toleration have not run out.

## 📚 Exercise 4: start the kubelet again

Start the kubelet again, wait until the node is ready, then read its taints
twice, ten seconds apart:

```bash
docker exec architecture-worker3 systemctl start kubelet
kubectl wait --for=condition=Ready node/architecture-worker3 --timeout=120s
kubectl describe node architecture-worker3 | grep -E '^Taints'
sleep 10
kubectl describe node architecture-worker3 | grep -E '^Taints'
```

```text
node/architecture-worker3 condition met
Taints:             node.kubernetes.io/unreachable:NoExecute
Taints:             <none>
```

The node is `Ready` before the `NoExecute` taint is removed: a few seconds
separate the two. Your witness Pod did not move:

```bash
kubectl get pods -n essai-noeud -o wide --field-selector spec.nodeName=architecture-worker3
```

```text
NAME                      READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE   READINESS GATES
temoin-556cf4ff8c-8w9th   1/1     Running   0          67s   10.244.4.12   architecture-worker3   <none>           <none>
```

Same name, no restart: the node came back before the end of the 300 seconds,
the Pod was not removed.

## 📚 Exercise 5: delete the kube-proxy of a node

**kube-proxy** prepares, on each node, the network rules that make Services
work. It runs as a **DaemonSet**, an object that places one Pod on each node.
Delete the one of `architecture-worker3`:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide --field-selector spec.nodeName=architecture-worker3
PROXY=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy --field-selector spec.nodeName=architecture-worker3 -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $PROXY -n kube-system
```

```text
NAME               READY   STATUS    RESTARTS   AGE   IP           NODE                   NOMINATED NODE   READINESS GATES
kube-proxy-p9gxx   1/1     Running   0          88s   172.18.0.4   architecture-worker3   <none>           <none>
pod "kube-proxy-p9gxx" deleted from kube-system namespace
```

Wait five seconds and look again:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide --field-selector spec.nodeName=architecture-worker3
kubectl get daemonset kube-proxy -n kube-system
```

```text
NAME               READY   STATUS    RESTARTS   AGE   IP           NODE                   NOMINATED NODE   READINESS GATES
kube-proxy-jhhlg   1/1     Running   0          6s    172.18.0.4   architecture-worker3   <none>           <none>
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
kube-proxy   4         4         4       4            4           kubernetes.io/os=linux   15m
```

A new Pod, `kube-proxy-jhhlg`, already runs on the same node. The DaemonSet
wants one Pod per node: `DESIRED` is `4`, like the number of nodes. The Pod's
address, `172.18.0.4`, is the address of the node itself: kube-proxy uses the
machine's network, not an address from the `PodCIDR`.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace,
and the witness Pod with it.

```bash
kubectl delete namespace essai-noeud
```

```text
namespace "essai-noeud" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-lire-un-node
dsoxlab check k8s-lire-un-node
```

```text
╭──── Result: k8s-lire-un-node ─────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: fill the sheet of the `architecture-worker2`
node with what it declares about itself.

```bash
dsoxlab run k8s-lire-un-node
dsoxlab challenge k8s-lire-un-node
```
