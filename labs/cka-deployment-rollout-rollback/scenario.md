# Roll back a stuck rollout, then ship the right version

## The situation

In the namespace **`lab`**, the Deployment **`webapp`** runs with three
replicas. A colleague started the update to the new image this morning, with a
typo in its name. Since then, `kubectl rollout status` never returns: a new Pod
cannot pull its image, the three old ones keep the service up, and the
Deployment is going nowhere.

The expected image is **`nginx:1.27-alpine`**. Its tag is what counts: a digest
appended to that tag is accepted, any other tag is not.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. **First**, the version that worked, the one before the update, back in
   service: `nginx:1.26-alpine`, as the Deployment's **revision 3**. The stuck
   rollout must be left before anything else is shipped.

2. **Then**, the right image shipped: `webapp` on `nginx:1.27-alpine`, as the
   Deployment's **revision 4**, three replicas asked for, three replicas
   available and up to date, and no Pod left in image error.

3. The Deployment carries a **change cause**: the annotation
   `kubernetes.io/change-cause` on the **Deployment itself**, with text that
   says what was shipped. That is where the tests read it.

4. The history is intact. The ReplicaSet of the version that worked and the one
   of the faulty image are both still there, and the faulty one, which stays
   **revision 2**, is scaled down to **zero**: nothing was deleted by hand, and
   the Deployment was neither deleted nor recreated.

So, at the end, four revisions: 1 the original application, 2 this morning's
faulty update at zero, 3 the version that worked back in service at zero, 4 the
right image with its three replicas.

## Useful bearings

A Deployment keeps its old ReplicaSets, at zero, and numbers every template
change. Going back to the previous revision destroys nothing: the old
ReplicaSet is reactivated and receives a new revision number.

`kubectl rollout history`, `kubectl rollout undo` and `kubectl set image` are
the three moves, and `rollout undo` is the one the exam expects for step 1;
`kubectl describe deployment` says why the rollout is stuck, and
`kubectl get pods` shows the Pod that has no image. The container of the
template is named `nginx`.

## How you will know it works

The tests read the live cluster: the Deployment, the Pods and the ReplicaSets
that **belong** to it, with their revision annotations. They judge the state
reached, not the commands you typed, and they cannot tell a `rollout undo` from
a `set image` back to the previous image: both leave the same history.

```bash
dsoxlab check cka-deployment-rollout-rollback
```
