# Challenge: Trace a Pod back to its Deployment

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. In the **`replicasets`** namespace:

- the **`api`** Deployment runs three Pods, and it was updated once;
- the **`compte-absent`** Deployment asks for two Pods, and has none.

The **`~/replicasets/releve.txt`** file waits for what you read in the
cluster.

## 🎯 What you must obtain

1. After **`replicaset-actif`**: the name of the `api` ReplicaSet that carries
   its Pods today.

2. After **`replicaset-ancien`**: the name of the `api` ReplicaSet kept at
   zero Pods since the update.

3. After **`cause-failedcreate`**: the reason why the `compte-absent`
   ReplicaSet creates no Pod, as its events give it.

4. **`compte-absent` has its two Pods available**, and it is **the same
   Deployment** as at the start: you repaired it, not recreated it.

## 🧭 Useful landmarks

A Deployment creates one ReplicaSet per version of its Pods, and it is the
ReplicaSet that creates the Pods. A ReplicaSet's name is its Deployment's,
followed by a fingerprint. The columns of `kubectl get replicaset` say which
one carries the Pods. The `ownerReferences` field links each object to its
owner.

When a Deployment has no Pod, the list of Pods says nothing, since it is
empty. Go up one level: it is the ReplicaSet that tried to create the Pods, and
the cause of the failure is in **its** events, at the end of
`kubectl describe`.

To repair, remove the cause without deleting the Deployment: either create
what is missing, or change the description of the Pods so it no longer asks
for it. The ReplicaSet tries again on its own, waiting a little longer after
each failure: after a long pause, it can take several minutes.
`kubectl rollout restart` has a new ReplicaSet created right away, without
recreating the Deployment.

## ✅ How you will know it is right

The tests read your file, then the `api` ReplicaSets and the state of
`compte-absent`. They also check that `compte-absent` is indeed the starting
Deployment.

```bash
dsoxlab check k8s-lire-les-replicasets
```
