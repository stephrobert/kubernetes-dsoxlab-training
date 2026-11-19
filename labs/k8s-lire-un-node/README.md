# Read what a worker Node declares

A **node** is a machine of the cluster. On each node, a program, the
**kubelet**, runs the Pods and keeps writing into the cluster what the machine
offers and how it is doing. In this course, you learn to read this
information, as in the lesson:

- the kubelet's **heartbeat**, which says the node is alive;
- the **overview** of all the nodes, then the **sheet** of a single one;
- **kube-proxy**, present on every node;
- what happens when a node **stops answering**.

You mostly read the `architecture-worker3` node. The challenge will ask you for
the sheet of another node: you will fill it on your own, at the end.

Related page: [How Kubernetes worker nodes work](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-lire-un-node
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`architecture` is running there, with one control plane and three workers, and
your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: see the kubelet's heartbeat

Every ten seconds, the kubelet renews a small object, a **lease**, named after
its node. List the leases:

```bash
kubectl get lease -n kube-node-lease
```

```text
NAME                         HOLDER                       AGE
architecture-control-plane   architecture-control-plane   10m
architecture-worker          architecture-worker          10m
architecture-worker2         architecture-worker2         10m
architecture-worker3         architecture-worker3         10m
```

One lease per node. Read the renewal time of `architecture-worker3`'s, twice,
ten seconds apart:

```bash
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
sleep 10
kubectl get lease -n kube-node-lease architecture-worker3 -o jsonpath='{.spec.renewTime}'; echo
```

```text
2026-11-19T11:12:13.857703Z
2026-11-19T11:12:23.871343Z
```

The time moved forward by ten seconds: the kubelet renewed its lease. As long
as it does, the cluster knows the node is alive.

## 📚 Exercise 2: see all the nodes at once

```bash
kubectl get nodes -o wide
```

```text
NAME                         STATUS   ROLES           AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                       KERNEL-VERSION                 CONTAINER-RUNTIME
architecture-control-plane   Ready    control-plane   10m   v1.37.0   172.18.0.2    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
architecture-worker          Ready    <none>          10m   v1.37.0   172.18.0.5    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
architecture-worker2         Ready    <none>          10m   v1.37.0   172.18.0.7    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
architecture-worker3         Ready    <none>          10m   v1.37.0   172.18.0.6    <none>        Debian GNU/Linux 13 (trixie)   6.12.117+deb13-amd64 (amd64)   containerd://2.3.4
```

Three columns answer the lesson's questions:

- `STATUS`: `Ready` means the kubelet reports a ready node;
- `VERSION`: the kubelet's version, here `v1.37.0`;
- `CONTAINER-RUNTIME`: the program that really starts the containers, and its
  version, here `containerd://2.3.4`.

## 📚 Exercise 3: show only the useful columns

The `-o custom-columns` option shows only the fields you choose, as
`TITLE:path.of.the.field`. Show the **capacity** of each node:

```bash
kubectl get nodes -o custom-columns=NOM:.metadata.name,CPU:.status.capacity.cpu,MEMOIRE:.status.capacity.memory,PODS:.status.capacity.pods
```

```text
NOM                          CPU   MEMOIRE     PODS
architecture-control-plane   2     4009780Ki   110
architecture-worker          2     4009780Ki   110
architecture-worker2         2     4009780Ki   110
architecture-worker3         2     4009780Ki   110
```

The four nodes have the same capacity: they are containers sharing the same
machine. On a real cluster, each node has its own. `PODS` is 110, the maximum
number of Pods per node.

## 📚 Exercise 4: read a node's sheet

`kubectl describe node` shows everything the cluster knows about a node. The
output is long: `sed` keeps one part of it at a time. Start with the
**conditions**:

```bash
kubectl describe node architecture-worker3 | sed -n '/^Conditions:/,/^Addresses:/p'
```

```text
Conditions:
  Type             Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message
  ----             ------  -----------------                 ------------------                ------                       -------
  MemoryPressure   False   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:01 +0000   KubeletHasSufficientMemory   kubelet has sufficient memory available
  DiskPressure     False   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:01 +0000   KubeletHasNoDiskPressure     kubelet has no disk pressure
  PIDPressure      False   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:01 +0000   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready            True    Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:02:16 +0000   KubeletReady                 kubelet is posting ready status
Addresses:
```

The first three conditions signal a problem when they are `True`: lack of
memory, disk or processes. `Ready`, on the other hand, must be `True`. A
healthy node therefore shows `False`, `False`, `False`, `True`.

Then read what the machine has and what is left for the Pods:

```bash
kubectl describe node architecture-worker3 | sed -n '/^Capacity:/,/^System Info:/p'
```

```text
Capacity:
  cpu:                2
  ephemeral-storage:  31491104768
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             4009780Ki
  pods:               110
Allocatable:
  cpu:                2
  ephemeral-storage:  31491104768
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             4009780Ki
  pods:               110
System Info:
```

`Capacity` is what the machine has. `Allocatable` is what is left for the Pods,
once the system's share is removed. Here both are equal, because kind reserves
nothing for the system.

Finally, the versions:

```bash
kubectl describe node architecture-worker3 | grep -E 'Container Runtime Version|Kubelet Version'
```

```text
  Container Runtime Version:  containerd://2.3.4
  Kubelet Version:            v1.37.0
```

These are the same values as the columns of exercise 2, read this time in the
node's sheet.

## 📚 Exercise 5: see kube-proxy on every node

**kube-proxy** sets up, on each node, the network rules that make Services
work. Its mode is read in its configuration:

```bash
kubectl -n kube-system get configmap kube-proxy -o yaml | grep 'mode:'
```

```text
    mode: iptables
```

It runs as a **DaemonSet**, an object that places one Pod on every node:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide
```

```text
NAME               READY   STATUS    RESTARTS   AGE   IP           NODE                         NOMINATED NODE   READINESS GATES
kube-proxy-6zbcq   1/1     Running   0          10m   172.18.0.7   architecture-worker2         <none>           <none>
kube-proxy-gsm7l   1/1     Running   0          10m   172.18.0.6   architecture-worker3         <none>           <none>
kube-proxy-hskwd   1/1     Running   0          10m   172.18.0.2   architecture-control-plane   <none>           <none>
kube-proxy-mscg7   1/1     Running   0          10m   172.18.0.5   architecture-worker          <none>           <none>
```

Look at the `NODE` column: exactly one `kube-proxy` Pod per node, control plane
included.

## 📚 Exercise 6: stop a node, then restart it

On kind, a node is a Docker container. Stop `architecture-worker3`'s (nothing
is destroyed), then look at the nodes right away:

```bash
docker stop architecture-worker3
kubectl get nodes
```

```text
architecture-worker3
NAME                         STATUS   ROLES           AGE   VERSION
architecture-control-plane   Ready    control-plane   10m   v1.37.0
architecture-worker          Ready    <none>          10m   v1.37.0
architecture-worker2         Ready    <none>          10m   v1.37.0
architecture-worker3         Ready    <none>          10m   v1.37.0
```

The node is still `Ready`: the cluster does not know yet that it stopped. Wait
a minute, then look again:

```bash
sleep 60
kubectl get nodes
```

```text
NAME                         STATUS     ROLES           AGE   VERSION
architecture-control-plane   Ready      control-plane   11m   v1.37.0
architecture-worker          Ready      <none>          11m   v1.37.0
architecture-worker2         Ready      <none>          11m   v1.37.0
architecture-worker3         NotReady   <none>          11m   v1.37.0
```

`NotReady`: the kubelet no longer renews its lease, and after about 50 seconds
the cluster considers it lost. Its sheet says so:

```bash
kubectl describe node architecture-worker3 | grep -E '^Taints|unreachable|^  Ready'
```

```text
Taints:             node.kubernetes.io/unreachable:NoExecute
                    node.kubernetes.io/unreachable:NoSchedule
  Ready            Unknown   Thu, 19 Nov 2026 11:10:52 +0000   Thu, 19 Nov 2026 11:13:14 +0000   NodeStatusUnknown   Kubelet stopped posting node status.
```

The `Ready` condition is `Unknown`, with the message `Kubelet stopped posting
node status`. The cluster also set two `unreachable` **marks** (taints): no
new Pod will go to this node anymore. Restart it and wait for it to come back:

```bash
docker start architecture-worker3
kubectl wait --for=condition=Ready node/architecture-worker3 --timeout=120s
kubectl get nodes
```

```text
architecture-worker3
node/architecture-worker3 condition met
NAME                         STATUS   ROLES           AGE   VERSION
architecture-control-plane   Ready    control-plane   11m   v1.37.0
architecture-worker          Ready    <none>          11m   v1.37.0
architecture-worker2         Ready    <none>          11m   v1.37.0
architecture-worker3         Ready    <none>          11m   v1.37.0
```

The node is `Ready` again.

## 🧹 Clean up

The exercises created nothing: you only read, then stopped and restarted a
node. Leave the machine and reset the lab. `dsoxlab reset` replays the lab's
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
