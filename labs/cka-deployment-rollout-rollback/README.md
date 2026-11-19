# Roll back a stuck rollout

A Deployment keeps the history of its versions. Each change to its Pod
template (a new image, for example) creates a numbered **revision**, and the
old version stays in reserve, with zero Pods. When an update goes wrong, you
can therefore **roll back** in one command, without rebuilding anything. In
this course, you ship a new image, you write down the reason for the change,
you cause a rollout that gets stuck, then you go back to a version that works.

You work in a scratch namespace, `essai-rollout`, with a Deployment `vitrine`.
The challenge will ask you for the same work on another Deployment, already
stuck: you will do it on your own, at the end.

Related page: [Kubernetes Deployments](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/deployments/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-deployment-rollout-rollback
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: create a Deployment and read its history

Create the scratch namespace and a `vitrine` Deployment with two Pods, on
nginx 1.30.5:

```bash
kubectl create namespace essai-rollout
kubectl create deployment vitrine --replicas=2 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
namespace/essai-rollout created
deployment.apps/vitrine created
Waiting for deployment "vitrine" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "vitrine" rollout to finish: 1 of 2 updated replicas are available...
deployment "vitrine" successfully rolled out
```

`kubectl rollout status` follows the rollout and gives the prompt back when
all the Pods are ready. Now read the history:

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
```

A single revision, number 1. The `CHANGE-CAUSE` column says why a revision
exists. It is empty (`<none>`): nobody has filled it in yet.

## 📚 Exercise 2: ship a new image

`kubectl set image` changes the image of a container in the Deployment. Here,
the container is called `nginx`, like the starting image:

```bash
kubectl set image deployment/vitrine \
  nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 \
  -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
deployment.apps/vitrine image updated
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

The Pods are replaced one by one. Look at the history, then at the
ReplicaSets of the namespace. A ReplicaSet is the object that runs the Pods of
one version. The command shows, for each one, its revision number, its image
and its number of ready Pods:

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         <none>

NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   2          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2
vitrine-8469487455   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

Two revisions, and one ReplicaSet for each. The one of revision 1 has no Pod
left (`<none>` means zero), but it is still there: it is the one used to roll
back.

## 📚 Exercise 3: write down the cause of the change

The cause of a revision comes from the `kubernetes.io/change-cause`
annotation, set on the Deployment. Write it:

```bash
kubectl annotate deployment vitrine kubernetes.io/change-cause='passage en nginx 1.30.6' -n essai-rollout
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine annotated
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         passage en nginx 1.30.6
```

The current revision, number 2, now has its reason ("passage en nginx 1.30.6"
means "move to nginx 1.30.6"). Keep in mind that this annotation stays on the
Deployment: you will see what that does at the next change.

## 📚 Exercise 4: a rollout that gets stuck

By default, a Deployment waits 10 minutes before declaring that a rollout no
longer makes progress. To avoid waiting that long, bring this delay down to
30 seconds with the `progressDeadlineSeconds` field:

```bash
kubectl patch deployment vitrine -n essai-rollout -p '{"spec":{"progressDeadlineSeconds":30}}'
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine patched
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         passage en nginx 1.30.6
```

No new revision: this field does not touch the Pod template. Now ship an image
that does not exist, `nginx:1.30.99`, as if you had made a typo:

```bash
kubectl set image deployment/vitrine nginx=nginx:1.30.99 -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=60s
```

```text
deployment.apps/vitrine image updated
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
error: deployment "vitrine" exceeded its progress deadline
```

The rollout is stuck. Look at the Pods:

```bash
kubectl get pods -n essai-rollout
```

```text
NAME                       READY   STATUS         RESTARTS   AGE
vitrine-56d8956678-hbc6x   1/1     Running        0          40s
vitrine-56d8956678-w8rqc   1/1     Running        0          48s
vitrine-75b7b686f9-9mz6h   0/1     ErrImagePull   0          31s
```

The new Pod cannot download its image (`ErrImagePull`). The two old Pods are
still running: Kubernetes removes an old Pod only once the new one is ready.
The service is not cut, but the rollout no longer moves. The ReplicaSets show
it too:

```bash
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   2          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2
vitrine-75b7b686f9   3          nginx:1.30.99                                                                          <none>
vitrine-8469487455   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

Revision 3 exists, with zero ready Pods. To know why the Deployment no longer
moves, read its conditions (`sed` cuts the output of `describe` to keep only
that block):

```bash
kubectl describe deployment vitrine -n essai-rollout | sed -n '/^Conditions:/,/^OldReplicaSets/p'
```

```text
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    False   ProgressDeadlineExceeded
OldReplicaSets:  vitrine-8469487455 (0/0 replicas created), vitrine-56d8956678 (2/2 replicas created)
```

`Available True`: enough Pods answer. `Progressing False` with
`ProgressDeadlineExceeded`: the rollout went past its deadline.

## 📚 Exercise 5: read a revision before going back to it

Before rolling back, look at the history:

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
2         passage en nginx 1.30.6
3         passage en nginx 1.30.6
```

Revision 3, the one with the faulty image, shows "passage en nginx 1.30.6".
That is wrong, but it is expected: the annotation had stayed on the
Deployment, and each new revision copies it. **After each change, write the
cause again**, otherwise the history lies.

To see what a revision holds before going back to it, add `--revision`:

```bash
kubectl rollout history deployment/vitrine -n essai-rollout --revision=2
```

```text
deployment.apps/vitrine with revision #2
Pod Template:
  Labels:	app=vitrine
	pod-template-hash=56d8956678
  Annotations:	kubernetes.io/change-cause: passage en nginx 1.30.6
  Containers:
   nginx:
    Image:	nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
    Port:	<none>
    Host Port:	<none>
    Environment:	<none>
    Mounts:	<none>
  Volumes:	<none>
  Node-Selectors:	<none>
  Tolerations:	<none>
```

Revision 2 is indeed nginx 1.30.6, the one that worked.

## 📚 Exercise 6: go back to the previous revision

`kubectl rollout undo` goes back to the revision just before the current one:

```bash
kubectl rollout undo deployment/vitrine -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
deployment.apps/vitrine rolled back
deployment "vitrine" successfully rolled out
```

The rollback is immediate: the Pods of revision 2 were still running. Read the
history and the ReplicaSets:

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
1         <none>
3         passage en nginx 1.30.6
4         passage en nginx 1.30.6

NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   4          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2
vitrine-75b7b686f9   3          nginx:1.30.99                                                                          <none>
vitrine-8469487455   1          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   <none>
```

Revision 2 is gone from the list, and a revision 4 has appeared. It is the
same ReplicaSet (`vitrine-56d8956678`), which got a **new number**. A rollback
destroys nothing: it reactivates the old ReplicaSet and renumbers it. The
faulty ReplicaSet stays there, with zero Pods. Its failing Pod is being
deleted:

```bash
kubectl get pods -n essai-rollout
```

```text
NAME                       READY   STATUS        RESTARTS   AGE
vitrine-56d8956678-hbc6x   1/1     Running       0          40s
vitrine-56d8956678-w8rqc   1/1     Running       0          48s
vitrine-75b7b686f9-9mz6h   0/1     Terminating   0          31s
```

## 📚 Exercise 7: go back to a given revision

`--to-revision` goes back to any revision of the history, not only the
previous one. Go back to the very first one, nginx 1.30.5:

```bash
kubectl rollout undo deployment/vitrine --to-revision=1 -n essai-rollout
kubectl rollout status deployment/vitrine -n essai-rollout --timeout=180s
```

```text
deployment.apps/vitrine rolled back
Waiting for deployment "vitrine" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

This time, the Pods are replaced one by one, as in a normal rollout. Look at
the result:

```bash
kubectl rollout history deployment/vitrine -n essai-rollout
kubectl get rs -n essai-rollout -o custom-columns='NOM:.metadata.name,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image,PODS:.status.readyReplicas'
```

```text
deployment.apps/vitrine
REVISION  CHANGE-CAUSE
3         passage en nginx 1.30.6
4         passage en nginx 1.30.6
5         <none>

NOM                  REVISION   IMAGE                                                                                  PODS
vitrine-56d8956678   4          nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   <none>
vitrine-75b7b686f9   3          nginx:1.30.99                                                                          <none>
vitrine-8469487455   5          nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   2
```

The ReplicaSet of revision 1 has become revision 5, and holds the two Pods.
Its cause is empty: a rollback also brings back the cause of the chosen
revision, and revision 1 had none. Here again, the cause should be written
again.

## 🧹 Clean up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-rollout
```

```text
namespace "essai-rollout" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-deployment-rollout-rollback
dsoxlab check cka-deployment-rollout-rollback
```

```text
╭─ Result: cka-deployment-rollout-rollback ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests          │
╰───────────────────────────────────────────╯
```

0 out of 8: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a Deployment is stuck on an image that does
not exist. Go back to the version that worked, then ship the right image, with
its cause.

```bash
dsoxlab run cka-deployment-rollout-rollback
dsoxlab challenge cka-deployment-rollout-rollback
```
