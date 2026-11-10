# Tune a rolling update: maxSurge and maxUnavailable

## The situation

In the **`lab`** namespace, the Deployment **`webapp`** runs five replicas,
image `nginx:1.26-alpine`. The next update must move to
`nginx:1.27-alpine`, and the team has constraints: the cluster has no room
for more than **two extra Pods** during the switch, and the service
tolerates no more than **one unavailable Pod** at a time.

The Deployment was created with an explicit **`strategy.type: Recreate`**,
which respects neither of the two: `Recreate` kills *every* Pod before
starting a single new one, so the service goes down for the whole switch,
and it has no `maxSurge` nor `maxUnavailable` to tune.

## What you must achieve

1. The Deployment `webapp` has a **`RollingUpdate`** strategy, in place of
   the `Recreate` it carries today.

2. Its `maxSurge` is **2**.

3. Its `maxUnavailable` is **1**.

4. Its image has moved to **`nginx:1.27-alpine`**.

5. Its **five** replicas are **ready, up to date, and running the new
   image**. The exercise changes the strategy and the image, not the size of
   the Deployment: it still asks for five, and that is checked here too.

6. **Two revisions of `webapp` exist**, produced by this Deployment, the new
   image's one coming after the old image's one in the history.

7. The ReplicaSet of `nginx:1.27-alpine` carries **five ready replicas**.

8. The old ReplicaSets are **kept at zero**.

## Useful bearings

`Recreate` and `RollingUpdate` are the two strategies a Deployment can have,
and only the second one replaces Pods gradually. That is why `maxSurge` and
`maxUnavailable` live under `spec.strategy.rollingUpdate`: they only mean
something once the type is `RollingUpdate`.

A Deployment keeps its old ReplicaSets, at zero replicas: that is what makes
the rollback possible, and it is also what shows a replacement took place.
Each rollout gives the ReplicaSet it activates a higher
`deployment.kubernetes.io/revision` number, and every one of those
ReplicaSets carries an `ownerReferences` pointing back at the Deployment
that produced it. The tests read both: a ReplicaSet written by hand is not
a revision.

**Advice, and this one is not graded.** Set the strategy *before* triggering
the update: it is the strategy in place at that moment that drives the
replacement. Nothing can measure this after the fact, because a Deployment
keeps no trace of the strategy a past rollout ran under. On the exam nobody
will check the order either, and a switch played under the default strategy
is a switch the cluster may not have had room for.

## How you will know it works

The tests read the Deployment's strategy, its image, its replica count and
its ready replicas, then the ReplicaSets that belong to it, with their
revision numbers. The replica count is read together with the state of the
revision the Deployment declares active: being ready means being ready on
the new image, not on the one you started from.

```bash
dsoxlab check ckad-rolling-update-strategy
```
