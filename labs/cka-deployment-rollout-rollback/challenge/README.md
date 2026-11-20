# Challenge: Roll back a stuck rollout, then ship the right version

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`lab`** namespace, the **`catalogue`** Deployment runs three
Pods, on `nginx:1.30.5-alpine`.

This morning, a colleague wanted to update it, but picked the wrong image: he
shipped `busybox:1.38.0` instead of nginx. Since then, the update is stuck:

- a new Pod starts, then stops, again and again;
- the three old Pods still serve the traffic;
- `kubectl rollout status` does not give the prompt back.

The expected image is **`nginx:1.30.6-alpine`**. Its tag is what counts: you may add
a digest to this tag, but not pick another tag.

## 🎯 What you must obtain

1. **First**, put the version that worked, `nginx:1.30.5-alpine`, back in
   service. It must become **revision 3** of the Deployment. Leave the stuck update before
   shipping anything else.

2. **Then**, ship the right image: `catalogue` on `nginx:1.30.6-alpine`, as
   **revision 4**, with three Pods requested, three Pods available and up to
   date, and no Pod left failing.

3. The `catalogue` Deployment carries a **change cause**: the
   `kubernetes.io/change-cause` annotation, set on the Deployment itself, with
   a text that says what was shipped.

4. The history is intact. Do not delete any ReplicaSet by hand, and do not
   delete the Deployment. At the end, the history therefore has four
   revisions:

   - revision 2, this morning's faulty update, kept with zero Pods;
   - revision 3, the version that worked put back in service, with zero Pods;
   - revision 4, the right image, with its three Pods.

   Revision 1 no longer shows: when you go back to the version that worked,
   its ReplicaSet gets number 3.

## 🧭 Useful landmarks

A Deployment keeps its old ReplicaSets, with zero Pods, and gives a number to
each change of its Pods. Rolling back destroys nothing: the old ReplicaSet
comes back into service and gets a new number.

Three commands are enough: `kubectl rollout history`, `kubectl rollout undo`
and `kubectl set image`. The Deployment's container is called `nginx`.
`kubectl describe deployment` says why the update is stuck, and
`kubectl get pods` shows the Pod that stops in a loop.

The change cause stays on the Deployment, and each new revision copies it. A
rollback, on the other hand, brings back the cause of the chosen revision. So
set yours after the final delivery.

## ✅ How you will know it is right

The tests read the cluster: the Deployment, its Pods and its ReplicaSets, with
their revision numbers. They judge the state reached, not the commands typed.
So they cannot tell a `rollout undo` from a `set image` back to the old image:
both leave the same history.

```bash
dsoxlab check cka-deployment-rollout-rollback
```
