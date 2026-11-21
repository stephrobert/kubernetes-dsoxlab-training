# An agent on every node, including the control plane

The lesson shows a DaemonSet that places one Pod on every node. Agents run
this way (monitoring, logs, networking) often touch the node itself. This
course adds cases the lesson does not show: a port opened on every node with
`hostPort`, two DaemonSets fighting over that port, an agent that shares the
node's network without losing the cluster's DNS, and draining a node that
carries DaemonSet Pods.

You work in a scratch namespace, `essai-ds`, with two scratch DaemonSets,
`sentinelle` and `doublon` ("sentinel" and "duplicate"), and a Pod
`sonde-hote` ("host probe"). The challenge is about other objects: you will
do it on your own, at the end.

Related page: [DaemonSets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-daemonset-all-nodes
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The cluster has two
nodes: `k8s-cp.lab` and the worker `k8s-w1.lab`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🔌 Exercise 1: a port opened on every node

With `hostPort`, a container's port also opens on the address of the node
that carries the Pod. Create the namespace, then a `sentinelle` DaemonSet
whose agent answers its Pod name on port 9376, published on the node's port
19376:

```bash
kubectl create namespace essai-ds
cat <<YAML | kubectl apply -n essai-ds -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: sentinelle
spec:
  selector:
    matchLabels: {app: sentinelle}
  template:
    metadata:
      labels: {app: sentinelle}
    spec:
      containers:
        - name: agent
          image: registry.k8s.io/e2e-test-images/agnhost:2.53
          args: [serve-hostname, --port=9376]
          ports:
            - {containerPort: 9376, hostPort: 19376}
YAML
kubectl rollout status daemonset/sentinelle -n essai-ds --timeout=120s; kubectl get pods -n essai-ds -o wide | cut -c1-90
```

```text
namespace/essai-ds created
daemonset.apps/sentinelle created
Waiting for daemon set "sentinelle" rollout to finish: 0 of 1 updated pods are available...
daemon set "sentinelle" successfully rolled out
NAME               READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINAT
sentinelle-l9n54   1/1     Running   0          0s    10.244.38.126   k8s-w1.lab   <none> 
```

A single Pod, on `k8s-w1.lab`. Call port 19376 of each node:

```bash
for n in $(kubectl get nodes -o jsonpath='{.items[*].status.addresses[0].address}'); do printf '%s:19376 -> ' $n; curl -s -m 3 "http://$n:19376"; echo; done
```

```text
10.10.50.11:19376 -> 
10.10.50.12:19376 -> sentinelle-l9n54
```

The worker answers, the control plane does not: it has no Pod. The control
plane carries a taint that keeps away Pods that do not tolerate it,
DaemonSet Pods included. That is precisely the subject of the challenge.

## ⚔️ Exercise 2: two DaemonSets want the same port

Create a second, identical DaemonSet, `doublon`, which also asks for the
node's port 19376:

```bash
cat <<YAML | kubectl apply -n essai-ds -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: doublon
spec:
  selector:
    matchLabels: {app: doublon}
  template:
    metadata:
      labels: {app: doublon}
    spec:
      containers:
        - name: agent
          image: registry.k8s.io/e2e-test-images/agnhost:2.53
          args: [serve-hostname, --port=9376]
          ports:
            - {containerPort: 9376, hostPort: 19376}
YAML
sleep 10; kubectl get pods -n essai-ds -l app=doublon
```

```text
daemonset.apps/doublon created
NAME            READY   STATUS    RESTARTS   AGE
doublon-tgfrv   0/1     Pending   0          10s
```

Its Pod stays `Pending`. Read the reason given by the scheduler:

```bash
P=$(kubectl get pods -n essai-ds -l app=doublon -o name | head -1); kubectl get events -n essai-ds --field-selector involvedObject.name=${P#pod/} -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/2 nodes are available: 1 node(s) didn't have free ports for the requested pod ports, 1 node(s) didn't satisfy plugin(s) [NodeAffinity]. preemption: 0/2 nodes are available: 1 No preemption victims found for incoming pod, 1 Preemption is not helpful for scheduling.
```

Two reasons, one per node. On the worker, port 19376 is already taken by
`sentinelle` (`didn't have free ports`). The other node is refused by
`NodeAffinity`: each DaemonSet Pod is tied to one specific node, and cannot
go elsewhere. Two agents that publish the same `hostPort` therefore cannot
share a node. Delete `doublon`:

```bash
kubectl delete daemonset doublon -n essai-ds
```

```text
daemonset.apps "doublon" deleted from essai-ds namespace
```

## 🏠 Exercise 3: share the node's network without losing the cluster's DNS

A network agent often runs with `hostNetwork`. Create such a Pod and ask it
for the `kubernetes` Service's name:

```bash
kubectl run sonde-hote --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-ds --overrides='{"spec":{"hostNetwork":true}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sonde-hote -n essai-ds --timeout=120s; kubectl exec sonde-hote -n essai-ds -- nslookup -timeout=3 kubernetes.default.svc.cluster.local; echo "code $?"
```

```text
pod/sonde-hote created
pod/sonde-hote condition met
;; connection timed out; no servers could be reached

command terminated with exit code 1
code 1
```

No answer. With `hostNetwork`, the default DNS policy (`ClusterFirst`) gives
the Pod the node's DNS, which does not know the cluster's names. Recreate it
with `dnsPolicy: ClusterFirstWithHostNet`:

```bash
kubectl delete pod sonde-hote -n essai-ds; kubectl run sonde-hote --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-ds --overrides='{"spec":{"hostNetwork":true,"dnsPolicy":"ClusterFirstWithHostNet"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sonde-hote -n essai-ds --timeout=120s; kubectl exec sonde-hote -n essai-ds -- nslookup kubernetes.default.svc.cluster.local. | grep -A1 Name
```

```text
pod "sonde-hote" deleted from essai-ds namespace
pod/sonde-hote created
pod/sonde-hote condition met
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
```

The name resolves. A `hostNetwork` agent that must reach Services by name
needs this policy.

## 🚧 Exercise 4: drain a node that carries DaemonSet Pods

Simulate draining the worker with `--dry-run=server`: the API checks
everything, but nothing moves.

```bash
kubectl drain k8s-w1.lab --dry-run=server 2>&1 | tail -4
```

```text
There are pending nodes to be drained:
 k8s-w1.lab
cannot delete DaemonSet-managed Pods (use --ignore-daemonsets to ignore): calico-system/calico-node-8x2wb, calico-system/csi-node-driver-lh854, essai-ds/sentinelle-l9n54, kube-system/kube-proxy-rfprv
cannot delete Pods that declare no controller (use --force to override): essai-ds/sonde-hote
```

Two blockers. DaemonSet Pods cannot be evicted: the DaemonSet would recreate
them straight away on the same node. And `sonde-hote`, created without a
controller, would be lost for good. Delete `sonde-hote`, and run again with
`--ignore-daemonsets`:

```bash
kubectl delete pod sonde-hote -n essai-ds; kubectl drain k8s-w1.lab --dry-run=server --ignore-daemonsets --delete-emptydir-data 2>&1 | tail -6
```

```text
pod "sonde-hote" deleted from essai-ds namespace
node/k8s-w1.lab cordoned (server dry run)
Warning: ignoring DaemonSet-managed Pods: calico-system/calico-node-8x2wb, calico-system/csi-node-driver-lh854, essai-ds/sentinelle-l9n54, kube-system/kube-proxy-rfprv
evicting pod kube-system/coredns-7dc84c8f75-sckdv (server dry run)
node/k8s-w1.lab drained (server dry run)
```

The drain goes through: DaemonSet Pods stay on the node, the others would be
evicted (here, a CoreDNS Pod). The node has not moved, since everything was a
dry run:

```bash
kubectl get nodes
```

```text
NAME         STATUS   ROLES           AGE   VERSION
k8s-cp.lab   Ready    control-plane   35h   v1.37.2
k8s-w1.lab   Ready    <none>          35h   v1.37.2
```

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-ds
```

```text
namespace "essai-ds" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-daemonset-all-nodes
dsoxlab check cka-daemonset-all-nodes
```

```text
╭─ Result: cka-daemonset-all-nodes ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an agent on every node, the control plane
included, without removing its taint.

```bash
dsoxlab run cka-daemonset-all-nodes
dsoxlab challenge cka-daemonset-all-nodes
```
