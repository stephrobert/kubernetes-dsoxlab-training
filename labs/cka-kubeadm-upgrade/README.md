# Upgrade a cluster by one minor version, without interrupting what runs

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain
(25 % of the exam), competency "Perform a version upgrade on a Kubernetes
cluster using kubeadm".

**This was the CKA's last gap, and its clearest one**: the training teaches the
task, and no lab made it playable.

## Why it had to wait

Issue #32 classed it as blocked, and the 2026-09-17 measurement showed how to
unblock it:

| repository | published versions |
|---|---|
| `v1.37` | 1.37.0-1.1 |
| `v1.36` | 1.36.0-1.1, 1.36.1-1.1, 1.36.2-2.1, 1.36.3-1.1, 1.36.4-1.1 |

So there is **nothing to upgrade within 1.37**. The cluster must start at 1.36
for an upgrade to exist at all, and that is the **minor** upgrade the exam asks
for.

## This lab is the only one in the catalogue that rebuilds the cluster

Its `setup.yaml` first includes the standard base, which guarantees a healthy
cluster, then brings it back to **1.36.4** with a `kubeadm reset` and an `init`.
Its `cleanup.yaml` **upgrades** it back to 1.37.0. It upgrades, it does not
rebuild: a second `reset` would be far riskier than an upgrade.

Without that cleanup, two kinds of damage: the validator's snapshot would see a
different version from the starting one, and above all the **next** lab would
inherit a downgraded cluster.

Both files carry a version guard and are therefore idempotent: on a cluster
already at the right version, they touch nothing.

## What the test catches

The last test brings three checks together, deliberately:

| check | what it catches |
|---|---|
| **every** node's version | `kubeadm upgrade apply` does not upgrade the kubelet: a forgotten node announces the old version without anything breaking |
| no unschedulable node | a node drained for the upgrade and never brought back: the cluster runs with one node fewer, and nothing reports it |
| both replicas ready | already true BEFORE the work, so worthless alone; next to the other two, it tells a conducted upgrade from one that took the service with it |

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 40 minutes |
| Companion lesson | [Upgrading a Kubernetes cluster](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/mettre-a-jour-cluster-kubernetes/) |

```bash
dsoxlab run   cka-kubeadm-upgrade
dsoxlab check cka-kubeadm-upgrade
```
