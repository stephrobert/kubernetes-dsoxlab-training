# Drain a worker for maintenance, without cutting the service

## The situation

The worker **`k8s-w1.lab`** is due for a kernel update tonight, with a
reboot. The **`web`** application, in the **`lab`** namespace, runs four
replicas spread over the two nodes, and the service must not be interrupted
during the operation.

A Pod outside any controller, **`outil-diag`**, is also lying around on that
worker: a colleague started it by hand last week and it can disappear.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. A **PodDisruptionBudget** named **`web-pdb`**, in the `lab` namespace,
   guaranteeing that **at least two** Pods of `web` stay available at all
   times. It must target the application's Pods, not a made-up label.

2. The worker `k8s-w1.lab` **taken out of scheduling and then evicted** of
   every Pod that can be: those of `web` are recreated on the other node,
   `outil-diag` is deleted, and the network DaemonSet stays in place.

3. Once the maintenance is done, the worker **back in service**: it accepts
   Pods again.

4. A ConfigMap **`drain-evidence`** in `lab`, with two keys: `drained-node`
   holding the name of the drained node, and `status` holding `completed`.

## Useful bearings

Taking a node out of scheduling and evicting it are two distinct gestures,
and the order matters. Eviction goes through the eviction API, which honours
disruption budgets: that is what makes the operation safe, and it is also
what makes it wait when the budget is reached.

By default, eviction refuses what it would not know how to recreate: Pods
managed by a DaemonSet, those with no controller at all, and those carrying
`emptyDir` volumes. Each of these refusals has its own option, and the brief
says what to do about it.

## How you will know it works

The tests read the budget and its status, the creation time of each `web`
Pod and the node carrying it, the state of the worker, and the ConfigMap.

```bash
dsoxlab check cka-node-drain-cordon
```
