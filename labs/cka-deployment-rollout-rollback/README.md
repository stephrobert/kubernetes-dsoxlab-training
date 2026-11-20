# Roll back a stuck rollout

A Deployment keeps the history of its versions. Each change to the template of
its Pods creates a numbered **revision**, and the old version stays in
reserve, with zero Pods. The lesson ships a wrong image, rolls back, then
ships the right image. This course takes another failure: a rollout that is
stuck although the image is fine. You diagnose it through the conditions of
the Deployment, you roll back, then you see why changing the image does not
repair a failure that is not in the image.

You work in a scratch namespace, `essai-livraison`, with an `affiche`
Deployment. The challenge will ask you to repair another Deployment, already
stuck: you will do it on your own, at the end.

Related page: [Kubernetes Deployments](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/deployments/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-deployment-rollout-rollback
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: ship a first version

Write the `affiche` Deployment in a file. It carries a **readiness probe**
(readinessProbe): the kubelet queries port 80 every two seconds, and the Pod
only receives traffic if nginx answers. `progressDeadlineSeconds: 30` tells
the Deployment to report a rollout that no longer moves after 30 seconds.

```bash
kubectl create namespace essai-livraison
cat > ~/essai-affiche.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: affiche
  namespace: essai-livraison
spec:
  replicas: 3
  progressDeadlineSeconds: 30
  selector:
    matchLabels:
      app: affiche
  template:
    metadata:
      labels:
        app: affiche
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 2
EOF
kubectl apply -f ~/essai-affiche.yaml
kubectl rollout status deployment/affiche -n essai-livraison --timeout=120s
kubectl rollout history deployment/affiche -n essai-livraison
```

```text title="Excerpt of the output"
namespace/essai-livraison created
deployment.apps/affiche created
deployment "affiche" successfully rolled out
deployment.apps/affiche
REVISION  CHANGE-CAUSE
1         <none>
```

One revision, number 1.

## 📚 Exercise 2: diagnose a stuck rollout

A colleague changes the probe and targets port 8080, where nginx does not
listen. Make the same mistake, then apply:

```bash
sed -i 's/port: 80/port: 8080/' ~/essai-affiche.yaml
kubectl apply -f ~/essai-affiche.yaml
kubectl rollout status deployment/affiche -n essai-livraison --timeout=45s
```

```text
deployment.apps/affiche configured
Waiting for deployment "affiche" rollout to finish: 1 out of 3 new replicas have been updated...
error: deployment "affiche" exceeded its progress deadline
```

`rollout status` gives up and exits with an error. Look at the Pods:

```bash
kubectl get pods -n essai-livraison
```

```text
NAME                       READY   STATUS    RESTARTS   AGE
affiche-576cfff896-wszxz   0/1     Running   0          31s
affiche-5b56f6c8d-9rnfc    1/1     Running   0          33s
affiche-5b56f6c8d-qjzp6    1/1     Running   0          33s
affiche-5b56f6c8d-vt674    1/1     Running   0          33s
```

The new Pod runs (`Running`) without any restart, but it is not ready
(`0/1`). Nothing crashes, and yet the rollout has stopped: the Deployment
waits for a new Pod to be ready before removing an old one. The three old
Pods still serve the traffic. The **conditions** of the Deployment sum it up:

```bash
kubectl describe deployment affiche -n essai-livraison | sed -n '/^Conditions:/,/^OldReplicaSets/p'
```

```text
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    False   ProgressDeadlineExceeded
OldReplicaSets:  affiche-5b56f6c8d (3/3 replicas created)
```

`Available True`: the service runs. `Progressing False` with
`ProgressDeadlineExceeded`: the rollout did not move in 30 seconds. The
reason is in the events of the Pod that is not ready:

```bash
POD=$(kubectl get pods -n essai-livraison -o jsonpath='{range .items[?(@.status.containerStatuses[0].ready==false)]}{.metadata.name}{end}')
kubectl describe pod $POD -n essai-livraison | grep -E 'Readiness|Unhealthy'
```

```text
    Readiness:      http-get http://:8080/ delay=0s timeout=1s period=2s successThreshold=1 failureThreshold=3
  Warning  Unhealthy  2s (x16 over 31s)  kubelet            spec.containers{nginx}: Readiness probe failed: Get "http://10.244.38.81:8080/": dial tcp 10.244.38.81:8080: connect: connection refused
```

The probe targets port 8080, and nothing answers there.

## 📚 Exercise 3: roll back, and see what runs

Before rolling back, note the two ReplicaSets:

```bash
kubectl get rs -n essai-livraison
```

```text
NAME                 DESIRED   CURRENT   READY   AGE
affiche-576cfff896   1         1         0       31s
affiche-5b56f6c8d    3         3         3       33s
```

Go back to the previous revision, and wait for the end:

```bash
kubectl rollout undo deployment/affiche -n essai-livraison
kubectl rollout status deployment/affiche -n essai-livraison --timeout=120s
```

```text
Warning: resource deployments/affiche was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/affiche rolled back
Waiting for deployment "affiche" rollout to finish: 1 old replicas are pending termination...
deployment "affiche" successfully rolled out
```

Keep this warning in mind: you will see its effect in exercise 5. Now look at
the ReplicaSets and the history:

```bash
kubectl get rs -n essai-livraison
kubectl rollout history deployment/affiche -n essai-livraison
```

```text
NAME                 DESIRED   CURRENT   READY   AGE
affiche-576cfff896   0         0         0       31s
affiche-5b56f6c8d    3         3         3       33s
deployment.apps/affiche
REVISION  CHANGE-CAUSE
2         <none>
3         <none>
```

No new ReplicaSet: `affiche-5b56f6c8d`, the one of revision 1, took the
service back and now carries number 3. Check what the Pods run:

```bash
kubectl get pods -n essai-livraison -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.spec.containers[0].image}{"\n"}{end}'
```

```text
affiche-576cfff896-wszxz  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
affiche-5b56f6c8d-9rnfc  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
affiche-5b56f6c8d-qjzp6  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
affiche-5b56f6c8d-vt674  nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

Both revisions had the same image: only the probe differed. The `wszxz` Pod
of the faulty revision is still listed: it is shutting down.

## 📚 Exercise 4: ship the next image and write its cause

Ship `nginx:1.30.6`, then write the reason for the change in the
`kubernetes.io/change-cause` annotation. Then fix that text:

```bash
kubectl set image deployment/affiche nginx=nginx:1.30.6 -n essai-livraison
kubectl rollout status deployment/affiche -n essai-livraison --timeout=120s
kubectl annotate deployment/affiche -n essai-livraison kubernetes.io/change-cause='passage à nginx 1.30.6'
kubectl annotate deployment/affiche -n essai-livraison kubernetes.io/change-cause='nginx 1.30.6, sonde sur le port 80'
kubectl rollout history deployment/affiche -n essai-livraison
```

```text title="Excerpt of the output"
deployment.apps/affiche image updated
deployment "affiche" successfully rolled out
deployment.apps/affiche annotated
deployment.apps/affiche annotated
deployment.apps/affiche
REVISION  CHANGE-CAUSE
2         <none>
3         <none>
4         nginx 1.30.6, sonde sur le port 80
```

The second `annotate` replaced the first text without any error. For this key,
`kubernetes.io/change-cause`, kubectl v1.37.2 replaces the old value directly.
For any other annotation, it refuses without the `--overwrite` option, with the
message `--overwrite is false but found the following declared annotation(s)`.
Adding `--overwrite` works in both cases.

## 📚 Exercise 5: changing the image does not repair a wrong probe

Your `~/essai-affiche.yaml` file still holds the probe on port 8080: the
rollback changed the cluster, not the file. Apply it again, as a colleague
picking up their work would, then look at the Pods about thirty seconds later:

```bash
kubectl apply -f ~/essai-affiche.yaml
kubectl get pods -n essai-livraison
```

```text
deployment.apps/affiche configured
NAME                       READY   STATUS    RESTARTS   AGE
affiche-576cfff896-6tc58   0/1     Running   0          35s
affiche-5fd8fdd64b-4d94t   1/1     Running   0          39s
affiche-5fd8fdd64b-csgw6   1/1     Running   0          37s
affiche-5fd8fdd64b-lwnss   1/1     Running   0          41s
```

The failure is back. The `affiche-576cfff896` ReplicaSet even comes back into
service: the file describes exactly the faulty revision. Try to repair by
changing the image:

```bash
kubectl set image deployment/affiche nginx=nginx:1.30.5 -n essai-livraison
kubectl rollout status deployment/affiche -n essai-livraison --timeout=45s
kubectl get deployment affiche -n essai-livraison -o jsonpath='{.spec.template.spec.containers[0].image} {.spec.template.spec.containers[0].readinessProbe.httpGet.port}{"\n"}'
```

```text title="Excerpt of the output"
deployment.apps/affiche image updated
error: deployment "affiche" exceeded its progress deadline
nginx:1.30.5 8080
```

New image, same blockage: `set image` only changes the image, and the probe
still targets port 8080. Look at what became of the history:

```bash
kubectl rollout history deployment/affiche -n essai-livraison
```

```text
deployment.apps/affiche
REVISION  CHANGE-CAUSE
3         <none>
4         nginx 1.30.6, sonde sur le port 80
5         nginx 1.30.6, sonde sur le port 80
6         nginx 1.30.6, sonde sur le port 80
```

Two more revisions, and the cause of revision 4 copied onto 5 and 6, where it
is wrong: the annotation stays on the Deployment, and each new revision takes
it over. Before shipping, look for what blocks: here `Unhealthy` in the events
of the Pod, not the image.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace and
the Deployment file.

```bash
kubectl delete namespace essai-livraison
rm ~/essai-affiche.yaml
```

```text
namespace "essai-livraison" deleted
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

Your turn, on your own this time: a Deployment is stuck on an image that stops in a
loop. Go back to the version that worked, then ship the right image, with
its cause.

```bash
dsoxlab run cka-deployment-rollout-rollback
dsoxlab challenge cka-deployment-rollout-rollback
```
