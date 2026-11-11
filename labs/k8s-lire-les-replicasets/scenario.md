# Trace a Pod back to its Deployment

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. In the **`replicasets`** namespace:

- the Deployment **`api`** runs three replicas, and it was updated once;
- the Deployment **`compte-absent`** asks for two replicas, and has none.

The record **`~/replicasets/releve.txt`** waits for what you read in the
cluster.

## What you must obtain

1. **`replicaset-actif`** gives the name of the ReplicaSet of `api` that
   carries its replicas today.

2. **`replicaset-ancien`** gives the name of the ReplicaSet of `api` kept at
   zero replicas since the update.

3. **`cause-failedcreate`** says why the ReplicaSet of `compte-absent` creates
   no Pod, as its events say it.

4. **`compte-absent` has its two replicas available**, and it is **the same
   Deployment** as at the start: it was repaired, not recreated.

## Useful landmarks

A Deployment does not create its Pods itself: it creates one ReplicaSet per
version of its Pod template, and the ReplicaSet creates the Pods. The name of a
ReplicaSet is the name of its Deployment followed by a hash of the template,
and the columns of `kubectl get replicaset` say which one carries the replicas.
`ownerReferences` links each object to its owner.

When a Deployment has no Pod, the list of Pods says nothing, since there are
none. Go up one level: the ReplicaSet tried to create the Pods, and the failure
is written in **its** events, at the end of `kubectl describe`.

To repair, remove the cause without deleting the Deployment: either create
what is missing, or correct the Pod template so it no longer asks for it. The
controller retries on its own, with a delay that grows after each failure:
after a long pause, it may wait several minutes. `kubectl rollout restart`
has a new ReplicaSet created at once, without recreating the Deployment.

## How you will know it is right

The tests read the record, then the ReplicaSets of `api` and the state of
`compte-absent`. The identity of `compte-absent` is compared with the one at
the start.

```bash
dsoxlab check k8s-lire-les-replicasets
```
