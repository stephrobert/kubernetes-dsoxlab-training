# Reserve a node: taint, toleration and nodeSelector

## The situation

The worker **`k8s-w1.lab`** has just been fitted with SSD disks, and the
team wants to **reserve it for production**: nothing else must be scheduled
on it, and the production application must go there, and nowhere else.

You are on the control plane, with `kubectl` configured. The **`lab`**
namespace exists.

## What you must achieve

1. The node `k8s-w1.lab` carries the taint **`env=prod:NoSchedule`** and the
   label **`disktype=ssd`**.

2. A Pod **`prod-app`** in `lab`, image `nginx:1.27-alpine`, that
   **tolerates** this taint and **requires** a `disktype=ssd` node. It runs
   on `k8s-w1.lab`.

3. A Pod **`dev-app`** in `lab`, same image, with neither toleration nor
   selector. It runs, but **not** on `k8s-w1.lab`.

## Useful bearings

A taint and a toleration only **allow**: a Pod that tolerates a taint may go
on that node, nothing forces it to. To **constrain** it to go there, you
also have to ask it for a node, through a `nodeSelector` on a label. Both
mechanisms are read in the Pod spec, and the tests look for them there: a
Pod pinned to the node with `nodeName` skips the scheduler, and the taint
with it, which is not the answer.

`kubectl describe node` shows the taints and the labels of a node;
`kubectl get pods -o wide` shows where each Pod landed.

## How you will know it works

The tests read the taints and the labels of the node, the actual node of
each Pod, and what the `prod-app` spec declares.

```bash
dsoxlab check cka-taints-tolerations-placement
```
