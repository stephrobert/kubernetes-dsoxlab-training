# Challenge: Watch the control plane reconcile

## 📍 The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your kubectl already targets it. In the **`reconciliation`** namespace, the
**`vitrine`** Deployment runs three Pods. The
**`~/reconciliation/releve.txt`** file waits for your answers.

## 🎯 What you must achieve

Two deletions, **in this order**. After each one, the cluster must come back
to the requested state.

1. You **deleted a Pod** of `vitrine`, and its ReplicaSet recreated it.

2. You then **deleted the ReplicaSet** of `vitrine`. It was replaced, and
   `vitrine` is back to **three available Pods**, without the Deployment being
   changed.

3. After **`pod-recree-par`**: the name of the controller that recreated the
   Pod.

4. After **`replicaset-recree-par`**: the name of the controller that
   recreated the ReplicaSet.

## 🧭 Useful pointers

You have nothing to restart by hand: the controllers fix the gap on their own.
To watch it happen, run `kubectl get pods -w` in a second terminal while you
delete.

Each controller signs what it does. When a ReplicaSet creates a Pod, it writes
a `SuccessfulCreate` event on itself. When a Deployment creates a ReplicaSet,
it writes a `ScalingReplicaSet` event on itself. The name to copy is in the
`From` column of `kubectl describe`, or in the `SOURCE` column of
`kubectl get events -o wide`.

Delete only the Pod, then only the ReplicaSet. Do not use
`kubectl rollout restart`: it also creates a new ReplicaSet, but by changing
the Deployment.

On this cluster, events are kept for **24 hours** (one hour by default in
Kubernetes). After a long break, those of the lab are gone: then run
`dsoxlab reset k8s-observer-la-reconciliation` again.

## ✅ How you will know it is right

The tests compare the cluster with the lab's starting state: the starting
ReplicaSet, its events, and the Deployment, which must not have been changed.

```bash
dsoxlab check k8s-observer-la-reconciliation
```
