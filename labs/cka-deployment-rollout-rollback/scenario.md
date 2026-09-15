# Roll back a stuck rollout, then ship the right version

## The situation

In the namespace **`lab`**, the Deployment **`webapp`** runs with three
replicas. A colleague started the update to the new image this morning, with a
typo in its name. Since then, `kubectl rollout status` never returns: a new Pod
cannot pull its image, the three old ones keep the service up, and the
Deployment is going nowhere.

The expected image is **`nginx:1.27-alpine`**.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. **First**, the Deployment brought back to the revision that worked, the one
   before the update, through its history. The stuck rollout must be undone
   before anything else is attempted.

2. **Then**, the right image shipped: `webapp` on `nginx:1.27-alpine`, three
   replicas available, no Pod in image error.

3. The final revision carries a **change cause**: the annotation
   `kubernetes.io/change-cause` on the Deployment, with text that says what
   was shipped.

4. The ReplicaSet of the faulty image is still there, scaled down to **zero**,
   as the history requires: nothing was deleted by hand.

## Useful bearings

A Deployment keeps its old ReplicaSets, at zero, and numbers every template
change. Rolling back destroys nothing: the old ReplicaSet is reactivated and
receives a new revision number. It is that number, on each ReplicaSet, that the
tests read to find out what happened and in what order.

`kubectl rollout history`, `kubectl rollout undo` and `kubectl set image` are
the three moves; `kubectl describe deployment` says why the rollout is stuck,
and `kubectl get pods` shows the Pod that has no image.

## How you will know it works

The tests read the Deployment, its Pods and its ReplicaSets with their revision
annotations.

```bash
dsoxlab check cka-deployment-rollout-rollback
```
