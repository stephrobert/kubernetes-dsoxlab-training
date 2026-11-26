# Scale out automatically with a HorizontalPodAutoscaler

The lesson shows a HorizontalPodAutoscaler (HPA) that adds replicas when CPU
consumption rises. This course adds cases the lesson does not show: a
minimum number of replicas applied without any load, a `kubectl scale` that
the HPA undoes, a target as an absolute memory value, and a side container
that skews the measurement, fixed by a per-container metric.

You work in a scratch namespace, `essai-hpa`, with two Deployments, `guichet`
("counter") and `mixte` ("mixed"). The challenge is about another
application: you will do it on your own, at the end.

Related page: [Horizontal Pod Autoscaling](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/horizontal-pod-autoscaling/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-hpa-autoscaling
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The lab installed
metrics-server, which gives the HPA the Pods' consumption.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and a one-replica `guichet` Deployment, with CPU and
memory requests and limits. An HPA computes its percentages from the
requests: without them, it cannot measure anything as a percentage.

```bash
kubectl create namespace essai-hpa; kubectl create deployment guichet --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=1 -n essai-hpa >/dev/null; kubectl set resources deployment guichet -n essai-hpa --requests=cpu=50m,memory=32Mi --limits=cpu=200m,memory=64Mi >/dev/null; kubectl rollout status deployment/guichet -n essai-hpa --timeout=120s
```

```text
namespace/essai-hpa created
Waiting for deployment "guichet" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "guichet" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "guichet" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "guichet" rollout to finish: 1 old replicas are pending termination...
deployment "guichet" successfully rolled out
```

## ⬆️ Exercise 1: minReplicas scales up without waiting for load

Create an HPA on `guichet`, with a minimum of 3 replicas and a target of
100 Mi of memory per Pod, far above what nginx consumes:

```bash
cat <<'YAML' | kubectl apply -n essai-hpa -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: guichet
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: guichet}
  minReplicas: 3
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: memory
        target: {type: AverageValue, averageValue: 100Mi}
YAML
sleep 20; kubectl get deployment guichet -n essai-hpa; kubectl get hpa guichet -n essai-hpa
```

```text
horizontalpodautoscaler.autoscaling/guichet created
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
guichet   3/3     3            3           21s
NAME      REFERENCE            TARGETS                MINPODS   MAXPODS   REPLICAS   AGE
guichet   Deployment/guichet   memory: 3332Ki/100Mi   3         5         3          20s
```

The Deployment went from 1 to 3 replicas although no load justifies it: the
average memory (3332 Ki) is far from the target. `minReplicas` is a floor
that the HPA applies as soon as it is created.

## ↩️ Exercise 2: a kubectl scale that the HPA undoes

Bring the Deployment back to one replica by hand, then look at it 30 seconds
later:

```bash
kubectl scale deployment guichet -n essai-hpa --replicas=1; kubectl get deployment guichet -n essai-hpa; sleep 30; kubectl get deployment guichet -n essai-hpa
```

```text
deployment.apps/guichet scaled
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
guichet   3/1     3            3           21s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
guichet   3/3     3            3           51s
```

Right after the command, the Deployment asks for one replica, and two Pods
are stopping. Thirty seconds later, it has 3 again. The HPA's events say why:

```bash
kubectl get events -n essai-hpa --field-selector involvedObject.kind=HorizontalPodAutoscaler,involvedObject.name=guichet,reason=SuccessfulRescale -o custom-columns=RAISON:.reason,MESSAGE:.message --no-headers
```

```text
SuccessfulRescale   New size: 3; reason: Current number of replicas below Spec.MinReplicas
```

A Deployment driven by an HPA can no longer be set by hand: the HPA takes over
again on its next pass. To change the number of replicas, change
`minReplicas` and `maxReplicas`.

## 📦 Exercise 3: a target as an average memory value

Replace the HPA with one going from 1 to 4 replicas, targeting 2 Mi of memory
on average per Pod (`AverageValue`), then look at it one minute later:

```bash
kubectl delete hpa guichet -n essai-hpa; cat <<'YAML' | kubectl apply -n essai-hpa -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: guichet
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: guichet}
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: Resource
      resource:
        name: memory
        target: {type: AverageValue, averageValue: 2Mi}
YAML
sleep 60; kubectl get hpa guichet -n essai-hpa; kubectl top pods -n essai-hpa
```

```text
horizontalpodautoscaler.autoscaling "guichet" deleted from essai-hpa namespace
horizontalpodautoscaler.autoscaling/guichet created
NAME      REFERENCE            TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
guichet   Deployment/guichet   memory: 3350Ki/2Mi   1         4         4          60s
NAME                       CPU(cores)   MEMORY(bytes)   
guichet-6f6b6549d8-484hw   0m           3Mi             
guichet-6f6b6549d8-6qgnc   0m           3Mi             
guichet-6f6b6549d8-99gfl   0m           3Mi             
guichet-6f6b6549d8-w4pq7   0m           3Mi             
```

The HPA went up to the maximum, 4. Each nginx Pod consumes about 3 Mi, and
adding Pods does not lower each one's memory: the target will never be
reached. A memory target only makes sense if each Pod's consumption drops
when the load is spread.

## 🔍 Exercise 4: a side container skews the measurement

Create a `mixte` Deployment whose Pods each have two containers:
`application` (nginx, idle) and `compteur` ("counter"), a loop that eats all
the CPU it is given. Add an HPA at 60% CPU, and look at it after 75 seconds:

```bash
cat <<YAML | kubectl apply -n essai-hpa -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mixte
spec:
  replicas: 1
  selector:
    matchLabels: {app: mixte}
  template:
    metadata:
      labels: {app: mixte}
    spec:
      containers:
        - name: application
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          resources:
            requests: {cpu: 50m}
            limits: {cpu: 100m}
        - name: compteur
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "while :; do :; done"]
          resources:
            requests: {cpu: 50m}
            limits: {cpu: 100m}
YAML
kubectl rollout status deployment/mixte -n essai-hpa --timeout=120s; kubectl autoscale deployment mixte -n essai-hpa --min=1 --max=4 --cpu=60%; sleep 75; kubectl get hpa mixte -n essai-hpa; kubectl top pods -n essai-hpa -l app=mixte --containers
```

```text
deployment.apps/mixte created
Waiting for deployment "mixte" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "mixte" rollout to finish: 0 of 1 updated replicas are available...
deployment "mixte" successfully rolled out
horizontalpodautoscaler.autoscaling/mixte autoscaled
NAME    REFERENCE          TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
mixte   Deployment/mixte   cpu: 100%/60%   1         4         2          75s
POD                      NAME          CPU(cores)   MEMORY(bytes)   
mixte-5bc776945d-j6zgc   application   0m           3Mi             
mixte-5bc776945d-j6zgc   compteur      101m         0Mi             
mixte-5bc776945d-nww54   application   0m           3Mi             
mixte-5bc776945d-nww54   compteur      100m         0Mi             
```

The HPA measures 101% and doubled the replicas. Yet the application is idle
(0m): `compteur` is the one consuming. A `Resource` metric adds up all of the
Pod's containers. Replace it with a `ContainerResource` metric, which only
measures the `application` container. The new HPA has another name: the
controller remembers an HPA's recent recommendations by its name, and an HPA
recreated under the same name would inherit them.

```bash
kubectl delete hpa mixte -n essai-hpa; kubectl scale deployment mixte -n essai-hpa --replicas=1; cat <<'YAML' | kubectl apply -n essai-hpa -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mixte-application
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: mixte}
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: ContainerResource
      containerResource:
        name: cpu
        container: application
        target: {type: Utilization, averageUtilization: 60}
YAML
sleep 75; kubectl get hpa mixte-application -n essai-hpa; kubectl get deployment mixte -n essai-hpa
```

```text
horizontalpodautoscaler.autoscaling "mixte" deleted from essai-hpa namespace
deployment.apps/mixte scaled
horizontalpodautoscaler.autoscaling/mixte-application created
NAME                REFERENCE          TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
mixte-application   Deployment/mixte   cpu: 0%/60%   1         4         1          75s
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
mixte   1/1     1            1           2m32s
```

0%: the HPA now only sees the application, and the Deployment is back to one
replica. When a Pod holds side containers, measure the container that carries
the load.

## 🧹 Clean-up

Delete the scratch namespace. The HPAs and Deployments go with it:

```bash
kubectl delete namespace essai-hpa
```

```text
namespace "essai-hpa" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-hpa-autoscaling
dsoxlab check cka-hpa-autoscaling
```

```text
╭─── Result: cka-hpa-autoscaling ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an application to scale out automatically,
and a load to prove it.

```bash
dsoxlab run cka-hpa-autoscaling
dsoxlab challenge cka-hpa-autoscaling
```
