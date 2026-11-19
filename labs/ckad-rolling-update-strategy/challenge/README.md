# Challenge: Tune a rolling update: maxSurge and maxUnavailable

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`lab`** namespace, the **`webapp`** Deployment runs five
Pods, on `nginx:1.30.5`.

The next update must move to `nginx:1.30.6`. The team has two constraints:

- the cluster has no room for more than **two extra Pods** during the switch;
- the service cannot bear more than **one unavailable Pod** at a time.

But `webapp` was created with the **`Recreate`** strategy. It stops all the
Pods before starting a single new one: the service is down during the whole
switch. And it has neither `maxSurge` nor `maxUnavailable` to tune.

## 🎯 What you must obtain

1. The `webapp` Deployment has the **`RollingUpdate`** strategy, instead of
   `Recreate`.

2. Its `maxSurge` is **2**.

3. Its `maxUnavailable` is **1**.

4. Its image has moved to **`nginx:1.30.6`**.

5. Its **five** Pods are **ready, up to date and on the new image**. You change
   the strategy and the image, not the number of Pods: five are still needed.

6. **Two revisions of `webapp` exist**, created by this Deployment. The one of
   the new image comes after the one of the old image.

7. The ReplicaSet of `nginx:1.30.6` has **five ready Pods**.

8. The old ReplicaSets are **kept, with zero Pods**.

## 🧭 Useful landmarks

`maxSurge` and `maxUnavailable` go under `spec.strategy.rollingUpdate`. They
only make sense with the `RollingUpdate` type.

A Deployment keeps its old ReplicaSets, with zero Pods. Each image change gives
the new ReplicaSet a higher revision number (the
`deployment.kubernetes.io/revision` annotation). Each ReplicaSet also points to
the Deployment that created it (the `ownerReferences` field). The tests read
both: a ReplicaSet written by hand does not count as a revision.

**A piece of advice, not graded:** set the strategy **before** changing the
image. The strategy in place at the time of the change decides how the Pods
are replaced. No test can check it afterwards: a Deployment keeps no trace of
the strategy used during a past switch.

## ✅ How you will know it is right

The tests read the Deployment's strategy, its image, its number of Pods and
its ready Pods. They then read the ReplicaSets that belong to it, with their
revision numbers. The ready Pods must be ready on the new image, not on the
old one.

```bash
dsoxlab check ckad-rolling-update-strategy
```
