# Tune a rolling update: maxSurge and maxUnavailable

## The situation

In the **`lab`** namespace, the Deployment **`webapp`** runs five replicas,
image `nginx:1.26-alpine`. The next update must move to
`nginx:1.27-alpine`, and the team has constraints: the cluster has no room
for more than **two extra Pods** during the switch, and the service
tolerates no more than **one unavailable Pod** at a time.

The Deployment was created with the default strategy, which respects
neither of the two.

## What you must achieve

1. The Deployment `webapp` has a **`RollingUpdate`** strategy with
   `maxSurge` at **2** and `maxUnavailable` at **1**.

2. Its image has moved to **`nginx:1.27-alpine`**.

3. The update is **finished**: five replicas ready on the new image, and the
   old ReplicaSet scaled down to zero.

## Useful bearings

The strategy is set before the update is triggered, otherwise it is the
default strategy that drives the replacement. Set, then update, in that
order.

A Deployment keeps its old ReplicaSets, at zero replicas: that is what makes
the rollback possible, and it is also what proves an update took place.

## How you will know it works

The tests read the Deployment's strategy, its image and its ready replicas,
then its ReplicaSets, the old one and the new one.

```bash
dsoxlab check ckad-rolling-update-strategy
```
