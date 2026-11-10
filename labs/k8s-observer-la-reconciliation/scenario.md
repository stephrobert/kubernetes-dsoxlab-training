# Watch the control plane reconcile

## The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your `kubectl` already points at it. In the **`reconciliation`** namespace, the
**`vitrine`** Deployment runs three replicas. The survey
**`~/reconciliation/releve.txt`** waits for your answers.

## What you must achieve

Two deletions, **in this order**, each followed by a return to the requested
state:

1. One Pod of `vitrine` was **deleted**, and its ReplicaSet recreated it.

2. Then the **ReplicaSet** of `vitrine` was deleted, it was replaced, and
   `vitrine` is back to **three available replicas**, without the Deployment
   being modified.

3. **`pod-recree-par`** names the controller that recreated the Pod.

4. **`replicaset-recree-par`** names the controller that recreated the
   ReplicaSet.

## Useful pointers

Nobody restarts anything by hand: the controllers of the control plane keep
comparing the requested state with the observed state, and act on the
difference. Watch it happen with `kubectl get pods -w` in a second terminal
while you delete.

Each controller signs what it does. A ReplicaSet that creates a Pod writes a
`SuccessfulCreate` event on itself; a Deployment that creates a ReplicaSet
writes a `ScalingReplicaSet` event on itself. `kubectl describe` shows them in
the **From** column, `kubectl get events -o wide` in the SOURCE column.

Delete only the Pod, then only the ReplicaSet. A `kubectl rollout restart`
would also create a new ReplicaSet, but by changing the Deployment: that is
not what you are watching here.

Events are kept for **24 hours** on this cluster (one hour is the Kubernetes
default). After a longer break, those of the lab are gone: `dsoxlab reset k8s-observer-la-reconciliation`
lays the situation out again.

## How you will know it is right

The tests compare the cluster with the state the lab started from: the
initial ReplicaSet, its events, and the Deployment's generation.

```bash
dsoxlab check k8s-observer-la-reconciliation
```
