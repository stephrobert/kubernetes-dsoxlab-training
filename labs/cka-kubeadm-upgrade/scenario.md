# Upgrade a cluster by one minor version, without interrupting what runs

## The situation

The cluster is one **minor version** behind. Engineering management has
decided: the upgrade happens this week, and the monitoring application running
in the **`supervision`** namespace must not stop answering during the operation.

It is called **`sonde`** and runs in two replicas, spread across the nodes.

## What you must achieve

1. The API server announces version **v1.37.0**.

2. **Every node** announces that same version, control plane and worker
   included.

3. **No node is left unschedulable.**

4. The `sonde` application still has its **two** replicas ready.

All required packages are available on the nodes: you have no repository to
declare.

## Useful bearings

The order is not a preference: **the control plane first**, the nodes after. A
worker cannot get ahead of its control plane.

On the control plane, the tool driving the upgrade must **itself** be at the
target version before applying it, otherwise it does not know what that version
expects.

Kubernetes packages are **held** on these nodes: you must free them to change
them, and hold them again afterwards.

The most frequent trap: the command applying the version to the cluster **does
not upgrade the kubelet**. It handles the control plane components, not the
service running on each machine.

On a worker, the command is **not the same** as on the control plane.

Drain a node before touching it, so its Pods go elsewhere rather than vanish
with it. And **bring it back** afterwards: a drained node stays unschedulable
until you do, and the cluster then runs with one node fewer without anything
reporting it.

The worker is reached from the control plane with `ssh k8s-w1.lab`.

## How you will know it works

The last test reads **every** node's version, checks none was left
unschedulable, and that the application still has its two replicas. All three
are in the same test: upgrading the control plane while forgetting a node
leaves a cluster that works and is nonetheless wrong.

```bash
dsoxlab check cka-kubeadm-upgrade
```
