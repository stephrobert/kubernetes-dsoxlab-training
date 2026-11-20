# Tune a rolling update

When a Deployment changes its image, it replaces its Pods. Its **strategy**
says how:

- **`Recreate`** stops all the old Pods, then starts the new ones. The service
  is cut during the switch;
- **`RollingUpdate`** replaces the Pods little by little. The service keeps
  answering.

Two settings drive `RollingUpdate`. **`maxSurge`** says how many Pods beyond
the requested number may exist during the switch. **`maxUnavailable`** says how
many Pods may be missing. In this course, you compare the two strategies and
you see the effect of these two settings.

You work in a scratch namespace, `essai-strategie`, with three Deployments of
four Pods: `catalogue`, `panier` and `paiement`. The challenge will ask you for
other values on another Deployment: you will do it on your own, at the end.

Related page: [Kubernetes rolling updates and rollbacks](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-and-rollbacks/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-rolling-update-strategy
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: read the default strategy

Create the scratch namespace and a first Deployment, `catalogue`, with four
Pods:

```bash
kubectl create namespace essai-strategie
kubectl create deployment catalogue --replicas=4 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-strategie
kubectl rollout status deployment/catalogue -n essai-strategie --timeout=180s | tail -1
```

```text
namespace/essai-strategie created
deployment.apps/catalogue created
deployment "catalogue" successfully rolled out
```

You wrote no strategy. Read the one the Deployment got (the `spec.strategy`
field):

```bash
kubectl get deployment catalogue -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
{"rollingUpdate":{"maxSurge":"25%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

By default, a Deployment uses `RollingUpdate`, with `maxSurge` and
`maxUnavailable` at 25% of the requested number of Pods.

## 📚 Exercise 2: Recreate, stop everything then start everything again

Switch `catalogue` to `Recreate`:

```bash
kubectl patch deployment catalogue -n essai-strategie -p '{"spec":{"strategy":{"type":"Recreate"}}}'
```

```text
The Deployment "catalogue" is invalid: spec.strategy.rollingUpdate: Forbidden: may not be specified when strategy `type` is 'Recreate'
```

Refused. The `rollingUpdate` block of the default strategy is still there, and
`Recreate` does not want it: it has nothing to tune. You must remove that block
in the same command, by giving it the value `null`:

```bash
kubectl patch deployment catalogue -n essai-strategie -p '{"spec":{"strategy":{"type":"Recreate","rollingUpdate":null}}}'
kubectl get deployment catalogue -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
deployment.apps/catalogue patched
{"type":"Recreate"}
```

Now change the image, then read the Deployment's **events**. They tell, in
order, what it did with its ReplicaSets (the object that runs the Pods of one
version):

```bash
kubectl set image deployment/catalogue \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-strategie
kubectl rollout status deployment/catalogue -n essai-strategie --timeout=180s | tail -1
kubectl events --for deployment/catalogue -n essai-strategie
```

```text
deployment.apps/catalogue image updated
deployment "catalogue" successfully rolled out
LAST SEEN   TYPE     REASON              OBJECT                 MESSAGE
4s          Normal   ScalingReplicaSet   Deployment/catalogue   Scaled up replica set catalogue-75867bdb5 from 0 to 4
3s          Normal   ScalingReplicaSet   Deployment/catalogue   Scaled down replica set catalogue-75867bdb5 from 4 to 0
1s          Normal   ScalingReplicaSet   Deployment/catalogue   Scaled up replica set catalogue-5f44879b68 from 0 to 4
```

Read it line by line:

1. the creation: the old ReplicaSet goes from 0 to 4 Pods;
2. the old ReplicaSet goes **at once** from 4 to 0 Pods;
3. the new one goes from 0 to 4 Pods.

Between line 2 and line 3, no Pod runs: the service is cut.

## 📚 Exercise 3: RollingUpdate, one extra Pod at a time

Create a second Deployment, `panier`, which keeps the default strategy, and
tune it: at most **one** extra Pod during the switch (`maxSurge: 1`), and
**no** missing Pod (`maxUnavailable: 0`):

```bash
kubectl create deployment panier --replicas=4 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-strategie
kubectl rollout status deployment/panier -n essai-strategie --timeout=180s | tail -1
kubectl patch deployment panier -n essai-strategie -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0}}}}'
kubectl get deployment panier -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
deployment.apps/panier created
deployment "panier" successfully rolled out
deployment.apps/panier patched
{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0},"type":"RollingUpdate"}
```

Change the image and read the events:

```bash
kubectl set image deployment/panier \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-strategie
kubectl rollout status deployment/panier -n essai-strategie --timeout=180s | tail -1
kubectl events --for deployment/panier -n essai-strategie
```

```text
deployment.apps/panier image updated
deployment "panier" successfully rolled out
LAST SEEN   TYPE     REASON              OBJECT              MESSAGE
4s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-686df6f77c from 0 to 4
3s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 0 to 1
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 4 to 3
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 1 to 2
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 3 to 2
2s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 2 to 3
1s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 2 to 1
1s          Normal   ScalingReplicaSet   Deployment/panier   Scaled up replica set panier-86c6dbd4bd from 3 to 4
0s          Normal   ScalingReplicaSet   Deployment/panier   Scaled down replica set panier-686df6f77c from 1 to 0
```

This time, the switch happens one Pod at a time. The new ReplicaSet goes up by
one Pod (there are then 5, one more than the 4 requested). Once that Pod is
ready, the old one goes down by one Pod. And so on. There are always at least
4 ready Pods: the service is never cut.

## 📚 Exercise 4: percentages

`maxSurge` and `maxUnavailable` also accept a percentage of the requested
number of Pods. Create a third Deployment, `paiement`, with 50% extra and 25%
that may be missing:

```bash
kubectl create deployment paiement --replicas=4 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-strategie
kubectl rollout status deployment/paiement -n essai-strategie --timeout=180s | tail -1
kubectl patch deployment paiement -n essai-strategie -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":"50%","maxUnavailable":"25%"}}}}'
kubectl get deployment paiement -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
deployment.apps/paiement created
deployment "paiement" successfully rolled out
deployment.apps/paiement patched
{"rollingUpdate":{"maxSurge":"50%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

Percentages are written between quotes: `"50%"` is a text, `1` is a number.
On 4 Pods, 50% gives **2** extra Pods, and 25% gives **1** Pod that may be
missing. When the computation does not fall right, Kubernetes rounds
`maxSurge` up and `maxUnavailable` down: on 5 Pods, 25% gives 2 extra Pods
(1.25 rounded up) and 1 Pod that may be missing (1.25 rounded down). Check
the computation on 4 Pods in the events:

```bash
kubectl set image deployment/paiement \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-strategie
kubectl rollout status deployment/paiement -n essai-strategie --timeout=180s | tail -1
kubectl events --for deployment/paiement -n essai-strategie
```

```text
deployment.apps/paiement image updated
deployment "paiement" successfully rolled out
LAST SEEN   TYPE     REASON              OBJECT                MESSAGE
2s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-6d6f5b7db9 from 0 to 4
1s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-65dc89d74d from 0 to 2
1s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 4 to 3
1s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-65dc89d74d from 2 to 3
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 3 to 2
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled up replica set paiement-65dc89d74d from 3 to 4
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 2 to 1
0s          Normal   ScalingReplicaSet   Deployment/paiement   Scaled down replica set paiement-6d6f5b7db9 from 1 to 0
```

The new ReplicaSet starts with **two** Pods at once (`from 0 to 2`), and the
old one loses a Pod right away (`from 4 to 3`), without waiting. The switch is
faster than with `panier`, but it needs room for two extra Pods, and the
service runs for a while with one Pod less.

## 📚 Exercise 5: a refused setting

Try to forbid both extra Pods and missing Pods:

```bash
kubectl patch deployment paiement -n essai-strategie -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":0,"maxUnavailable":0}}}}'
kubectl get deployment paiement -n essai-strategie -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
The Deployment "paiement" is invalid: spec.strategy.rollingUpdate.maxUnavailable: Invalid value: 0: may not be 0 when `maxSurge` is 0
{"rollingUpdate":{"maxSurge":"50%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

Refused, and the strategy did not move. With 0 and 0, the Deployment could
neither add a new Pod nor remove an old one: the switch could never start. One
of the two settings must be at least 1.

## 📚 Exercise 6: the strategy makes no revision

You changed `paiement` twice: its strategy, then its image. Read its history
and its ReplicaSets (`-l app=paiement` keeps only its own):

```bash
kubectl rollout history deployment/paiement -n essai-strategie
kubectl get rs -n essai-strategie -l app=paiement -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PRETS:.status.readyReplicas'
```

```text
deployment.apps/paiement
REVISION  CHANGE-CAUSE
1         <none>
2         <none>

NOM                   REVISION   IMAGE                                                                                  PRETS
paiement-65dc89d74d   2          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   4
paiement-6d6f5b7db9   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

Only two revisions: the creation and the image change. Changing the strategy
created neither a revision nor a Pod, because it is not part of the Pod
template. It only serves **the next** replacement. So always set the strategy
**before** changing the image. The old ReplicaSet stays there, with zero Pods
(`<none>`), ready for a rollback.

## 🧹 Clean up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-strategie
```

```text
namespace "essai-strategie" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-rolling-update-strategy
dsoxlab check ckad-rolling-update-strategy
```

```text
╭─ Result: ckad-rolling-update-strategy ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests       │
╰────────────────────────────────────────╯
```

0 out of 8: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a Deployment on `Recreate` must move to a
progressive update, with precise limits, then change its image.

```bash
dsoxlab run ckad-rolling-update-strategy
dsoxlab challenge ckad-rolling-update-strategy
```
