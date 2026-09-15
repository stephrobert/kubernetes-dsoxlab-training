# Placing with nodeAffinity: required constraint and preference

## The situation

The **`storage-app`** application writes a lot and must only run on nodes
with fast disks, `ssd` or `nvme`. Among those, the team prefers the ones
carrying the label `storage-tier=fast`, without making it a requirement.
Only one node in the cluster has fast disks: **`k8s-w1.lab`**, which you
have to label.

A second application, **`gpu-app`**, demands an accelerator the cluster does
not have yet: it must be declared right now, wait, then start on its own the
day a node gets labelled.

You are on the control plane, with `kubectl` configured. The **`lab`**
namespace exists.

## What you must achieve

1. The node `k8s-w1.lab` carries the label **`disktype=ssd`**.

2. A **`storage-app`** Deployment in `lab`, three replicas, image
   `nginx:1.27-alpine`, with a **required** node affinity on `disktype`
   being `ssd` **or** `nvme`, and a **preferred** affinity of weight **80**
   on `storage-tier=fast`. Its three Pods are running.

3. A **`gpu-app`** Pod in `lab`, image `nginx:1.27-alpine`, with a required
   node affinity on **`accelerator=gpu`**. Declared before the label exists,
   it stays `Pending`.

4. The label **`accelerator=gpu`** set on `k8s-w1.lab`: `gpu-app` becomes
   `Running` without having been recreated.

## Useful bearings

`nodeAffinity` separates what is **required** for placement from what is
**preferred**; both have a long name ending in `IgnoredDuringExecution`, and
that suffix is what says an already placed Pod does not move if the label
changes afterwards. The `In`, `NotIn` and `Exists` operators allow more than
an equality.

A Pod left `Pending` because of an affinity says so in `kubectl describe
pod`, with the number of nodes that do not match. The scheduler retries on
its own as soon as a node changes.

## How you will know it works

The tests read the node labels, the affinities declared by `storage-app` and
`gpu-app`, and the actual node of each of their Pods.

```bash
dsoxlab check cka-node-affinity
```
