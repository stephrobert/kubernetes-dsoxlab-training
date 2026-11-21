# Apply a VPA recommendation

The lesson shows the VerticalPodAutoscaler (VPA): it watches the Pods'
consumption and recommends CPU and memory `requests`. This course adds cases
the lesson does not show: a cap set on the recommendation, a VPA that only
tunes CPU, a container left out of the calculation, and the `Initial` mode,
which only applies the recommendation to newly created Pods.

You work in a scratch namespace, `essai-vpa`, with a two-container
`atelier` ("workshop") Deployment and a VPA of the same name. The challenge is
about another application: you will do it on your own, at the end.

Related page: [Vertical Pod Autoscaling](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/vertical-pod-scaling/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-appliquer-une-recommandation-vpa
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The lab installed
metrics-server and the full VPA 1.8.1: the recommender that computes, the
updater that evicts, and the admission controller that changes Pods at
creation.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and the `atelier` Deployment. Each Pod has two
containers, each requesting 10m of CPU: `application`, a computing loop that
consumes more than that, and `journal` ("log"), which writes the date every
second.

```bash
kubectl create namespace essai-vpa; cat <<YAML | kubectl apply -n essai-vpa -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: atelier
spec:
  replicas: 2
  selector:
    matchLabels: {app: atelier}
  template:
    metadata:
      labels: {app: atelier}
    spec:
      containers:
        - name: application
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "while :; do i=0; while [ \$i -lt 20000 ]; do i=\$((i+1)); done; sleep 0.2; done"]
          resources:
            requests: {cpu: 10m, memory: 8Mi}
        - name: journal
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "while :; do date; sleep 1; done"]
          resources:
            requests: {cpu: 10m, memory: 8Mi}
YAML
kubectl rollout status deployment/atelier -n essai-vpa --timeout=120s
```

```text
namespace/essai-vpa created
deployment.apps/atelier created
Waiting for deployment "atelier" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "atelier" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "atelier" rollout to finish: 1 of 2 updated replicas are available...
deployment "atelier" successfully rolled out
```

## 🧢 Exercise 1: cap, and only tune CPU

Create a VPA in `Off` mode (it recommends, it does not act). For the
`application` container, it must only tune CPU (`controlledResources`),
without exceeding 30m (`maxAllowed`). The `journal` container is left out
(`mode: Off`). The command then waits for the recommendation to show up:

```bash
cat <<'YAML' | kubectl apply -n essai-vpa -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: atelier
spec:
  targetRef: {apiVersion: apps/v1, kind: Deployment, name: atelier}
  updatePolicy: {updateMode: "Off"}
  resourcePolicy:
    containerPolicies:
      - containerName: application
        controlledResources: [cpu]
        maxAllowed: {cpu: 30m}
      - containerName: journal
        mode: "Off"
YAML
for i in $(seq 1 30); do kubectl get vpa atelier -n essai-vpa -o jsonpath='{.status.recommendation}' | grep -q application && break; sleep 10; done; kubectl get vpa atelier -n essai-vpa
```

```text
verticalpodautoscaler.autoscaling.k8s.io/atelier created
NAME      MODE   CPU   MEM   PROVIDED   AGE
atelier   Off    30m         True       60s
```

The `CPU` column shows 30m, and the `MEM` column is empty: memory is not
tuned. Compare the applied target with the uncapped target (`cible` means
"target", `non plafonnée` means "uncapped"):

```bash
kubectl get vpa atelier -n essai-vpa -o jsonpath='{range .status.recommendation.containerRecommendations[*]}{.containerName}: cible={.target} non plafonnée={.uncappedTarget}{"\n"}{end}'
```

```text
application: cible={"cpu":"30m"} non plafonnée={"cpu":"109m"}
```

The recommender would have wanted 109m (`uncappedTarget`), the cap brings the
target down to 30m. `journal` does not show up at all: it is left out. The cap
keeps a container within the node's budget, whatever it consumes.

## 🐣 Exercise 2: the Initial mode only acts at creation

Switch the VPA to `Initial` mode, wait one minute, and read the CPU request of
the `application` container in each Pod:

```bash
kubectl patch vpa atelier -n essai-vpa --type merge -p '{"spec":{"updatePolicy":{"updateMode":"Initial"}}}'; sleep 60; kubectl get pods -n essai-vpa -o jsonpath='{range .items[*]}{.metadata.name} {.spec.containers[0].resources.requests.cpu}{"\n"}{end}'
```

```text
verticalpodautoscaler.autoscaling.k8s.io/atelier patched
atelier-84755569c8-2mwm4 10m
atelier-84755569c8-vrzjz 10m
```

Nothing changed: 10m everywhere. In `Initial` mode, the VPA never evicts a
running Pod. Delete one of the two Pods, let the Deployment recreate it, and
read the requests of both containers again:

```bash
P=$(kubectl get pods -n essai-vpa -o jsonpath='{.items[0].metadata.name}'); kubectl delete pod $P -n essai-vpa; kubectl rollout status deployment/atelier -n essai-vpa --timeout=120s; sleep 5; kubectl get pods -n essai-vpa -o jsonpath='{range .items[*]}{.metadata.name} application={.spec.containers[0].resources.requests} journal={.spec.containers[1].resources.requests} annotation={.metadata.annotations.vpaUpdates}{"\n"}{end}'
```

```text
pod "atelier-84755569c8-2mwm4" deleted from essai-vpa namespace
deployment "atelier" successfully rolled out
atelier-84755569c8-p74b8 application={"cpu":"30m","memory":"8Mi"} journal={"cpu":"10m","memory":"8Mi"} annotation=Pod resources updated by atelier: container 0: cpu request
atelier-84755569c8-vrzjz application={"cpu":"10m","memory":"8Mi"} journal={"cpu":"10m","memory":"8Mi"} annotation=
```

The new Pod got 30m for `application`, and the annotation left by the VPA's
admission controller confirms it. `journal` keeps its 10m, as does its memory:
only the controlled resources change. The old Pod is still at 10m. Finally,
look at the Deployment's template (`gabarit du Deployment` means "Deployment
template"):

```bash
kubectl get deployment atelier -n essai-vpa -o jsonpath='gabarit du Deployment : {.spec.template.spec.containers[0].resources.requests}{"\n"}'
```

```text
gabarit du Deployment : {"cpu":"10m","memory":"8Mi"}
```

Still 10m. The VPA changes Pods when they are created, never the Deployment.
To make a recommendation last, you must carry it over into the Deployment
itself.

## 🧹 Clean-up

Delete the scratch namespace. The VPA and the Deployment go with it:

```bash
kubectl delete namespace essai-vpa
```

```text
namespace "essai-vpa" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-appliquer-une-recommandation-vpa
dsoxlab check k8s-appliquer-une-recommandation-vpa
```

```text
╭─ Result: k8s-appliquer-une-recommandation-vpa ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests               │
╰────────────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a recommendation to obtain, then to apply
yourself to an application, without any Pod being evicted.

```bash
dsoxlab run k8s-appliquer-une-recommandation-vpa
dsoxlab challenge k8s-appliquer-une-recommandation-vpa
```
