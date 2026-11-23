# Spot the key signals of a cluster

The lesson presents the three metric sources of a cluster (kube-state-metrics,
cAdvisor and the kubelet), the five signals to watch, and the PromQL alerts
that catch them. This course has you read each source, trigger two signals
on scratch Pods, find them in Prometheus, then write an alert and watch it
fire.

You work in the `essai-obs` namespace. The challenge uses other Pods and
other signals: you will do it on your own, at the end.

Related page: [Kubernetes observability](https://www.stephane-robert.info/en/docs/devsecops/reliability/kubernetes-observability/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-reperer-les-signaux-d-un-cluster
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm
cluster (the control plane). Your kubectl already targets it. The lab
installed Prometheus in the `supervision` namespace: from this node, it
answers on `http://localhost:30090`.

To query Prometheus without a browser, define a small `q` function. It sends
a PromQL query to its API and prints each series on one line, with its
value:

```bash
q() { curl -fsS http://localhost:30090/api/v1/query --data-urlencode "query=$1" | jq -r '.data.result[] | "\(.metric | del(.__name__, .instance, .job, .uid, .id, .name, .image) | to_entries | map("\(.key)=\(.value)") | join(",")) => \(.value[1])"'; }
```

Keep the same terminal until the clean-up: the function only exists in it.
The outputs shown in this course were captured on this machine on
23 November 2026, with Kubernetes v1.37.2, Prometheus v3.16.0 and
kube-state-metrics v2.20.0.

## 🔍 Exercise 1: read the three sources by hand

Prometheus creates no metric: it reads them from three sources. Read each
one directly, through the API server proxy, and look for what it knows about
the same subject, the `supervision` namespace:

```bash
kubectl get --raw /api/v1/namespaces/kube-system/services/kube-state-metrics:http-metrics/proxy/metrics | grep -c '^kube_'
kubectl get --raw /api/v1/namespaces/kube-system/services/kube-state-metrics:http-metrics/proxy/metrics | grep '^kube_pod_status_phase{namespace="supervision"' | grep ' 1$'
kubectl get --raw /api/v1/nodes/k8s-cp.lab/proxy/metrics | grep '^kubelet_running_pods'
kubectl get --raw /api/v1/nodes/k8s-cp.lab/proxy/metrics/cadvisor | grep '^container_memory_working_set_bytes{' | grep 'namespace="supervision"' | grep 'container="prometheus"' | grep -o 'pod="[^"]*"} [0-9.e+]*'
```

```text
4138
kube_pod_status_phase{namespace="supervision",pod="prometheus-db77b7f4b-tsgq8",uid="98568c05-c952-4c60-9ca2-ec27b90beab7",phase="Running"} 1
kubelet_running_pods 24
pod="prometheus-db77b7f4b-tsgq8"} 9.1938816e+07
```

kube-state-metrics knows the **state** of objects: the Prometheus Pod is in
the `Running` phase. The kubelet knows its **node**: 24 Pods run on it.
cAdvisor knows the **consumption**: the Prometheus container uses about
92 MB of memory. None of the three knows what the other two know.

## ⏳ Exercise 2: a Pod that finds no room

Create a Pod that requests 64 CPUs, more than any node has, then ask
Prometheus which Pods of `essai-obs` are pending. Also look at the `Ready`
state of the nodes, the fourth signal of the lesson:

```bash
kubectl create namespace essai-obs
kubectl -n essai-obs run essai-trop-gros --image=busybox:1.37 --restart=Never --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.37","command":["sleep","3600"],"resources":{"requests":{"cpu":"64"}}}]}}'
sleep 40; kubectl -n essai-obs get pods
q 'kube_pod_status_phase{namespace="essai-obs",phase="Pending"} == 1'
q 'sum by (node) (kube_node_status_condition{condition="Ready",status="true"})'
```

```text
namespace/essai-obs created
pod/essai-trop-gros created
NAME              READY   STATUS    RESTARTS   AGE
essai-trop-gros   0/1     Pending   0          40s
namespace=essai-obs,phase=Pending,pod=essai-trop-gros => 1
node=k8s-cp.lab => 1
node=k8s-w1.lab => 1
node=k8s-w2.lab => 1
```

kube-state-metrics publishes one series per phase and per Pod, which is 1
for the current phase: `== 1` keeps only the Pods that are really pending.
The three nodes are at 1: they are all `Ready`. A failing node would be at 0,
and `== 0` would catch it.

## 🔁 Exercise 3: a container that keeps restarting

Create a Deployment whose container exits with an error after 5 seconds,
wait two minutes, then count its recent restarts:

```bash
kubectl -n essai-obs create deployment essai-plante --image=busybox:1.37 -- sh -c 'sleep 5; exit 1'
sleep 120; kubectl -n essai-obs get pods -l app=essai-plante
q 'increase(kube_pod_container_status_restarts_total{namespace="essai-obs"}[5m])'
q 'kube_pod_container_status_last_terminated_reason{namespace="essai-obs"}'
```

```text
deployment.apps/essai-plante created
NAME                          READY   STATUS   RESTARTS      AGE
essai-plante-757448f7-tj4v2   0/1     Error    3 (87s ago)   2m
container=busybox,namespace=essai-obs,pod=essai-plante-757448f7-tj4v2 => 2.1748000000000003
container=busybox,namespace=essai-obs,pod=essai-plante-757448f7-tj4v2,reason=Error => 1
```

`increase()` estimates the number of restarts over the last 5 minutes, from
a counter. The estimate is not a whole number: Prometheus extrapolates
between its measurements. The reason for the last stop is `Error`, a
non-zero exit code. A container killed for lack of memory would show
`OOMKilled`.

## 🚨 Exercise 4: write an alert and watch it fire

Prometheus reads its rules from the `prometheus-regles` ConfigMap of the
`supervision` namespace. Write a rule that alerts on a Pod of `essai-obs`
pending for more than a minute, store it in the ConfigMap, then wait for the
file to appear in the Prometheus Pod:

```bash
cat > essai-regles.yaml <<'YAML'
groups:
  - name: essai-obs
    rules:
      - alert: EssaiPodEnAttente
        expr: sum by (namespace, pod) (kube_pod_status_phase{namespace="essai-obs",phase="Pending"}) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Le Pod {{ $labels.pod }} attend depuis plus d'une minute"
YAML
kubectl -n supervision create configmap prometheus-regles --from-file=essai.yaml=essai-regles.yaml --dry-run=client -o yaml | kubectl apply -f -
until kubectl -n supervision exec deploy/prometheus -- ls /etc/prometheus/regles/ | grep -q essai.yaml; do sleep 5; done; echo "fichier présent"
```

```text
configmap/prometheus-regles configured
fichier présent
```

The file took about 70 seconds to reach the Pod: that is the update delay of
a mounted ConfigMap. Now ask Prometheus to read its rules again, then follow
the alert:

```bash
curl -s -X POST http://localhost:30090/-/reload -o /dev/null -w '%{http_code}\n'
sleep 20; curl -s http://localhost:30090/api/v1/alerts | jq -r '.data.alerts[] | "\(.labels.alertname) \(.labels.pod) \(.state)"'
sleep 60; curl -s http://localhost:30090/api/v1/alerts | jq -r '.data.alerts[] | "\(.labels.alertname) \(.labels.pod) \(.state) \(.annotations.summary)"'
```

```text
200
EssaiPodEnAttente essai-trop-gros pending
EssaiPodEnAttente essai-trop-gros firing Le Pod essai-trop-gros attend depuis plus d'une minute
```

The alert first goes through `pending`: the condition is true, but not yet
for the duration of its `for:`. A minute later, it is `firing`, and its
summary names the Pod. Without the `for:`, a Pod that waits a few seconds
during a normal rollout would wake up the on-call team.

## 🧹 Clean-up

Empty the rules ConfigMap, then restart Prometheus: it starts again with no
rule, as at the beginning of the lab. Finally delete the scratch namespace and
the rules file:

```bash
kubectl -n supervision create configmap prometheus-regles --dry-run=client -o yaml | kubectl apply -f -
kubectl -n supervision rollout restart deployment/prometheus
kubectl -n supervision rollout status deployment/prometheus --timeout=300s
kubectl delete namespace essai-obs --wait=true --timeout=120s
rm -f essai-regles.yaml
curl -s http://localhost:30090/api/v1/rules | jq '.data.groups | length'
```

```text
configmap/prometheus-regles configured
deployment.apps/prometheus restarted
Waiting for deployment "prometheus" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "prometheus" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "prometheus" rollout to finish: 1 old replicas are pending termination...
deployment "prometheus" successfully rolled out
namespace "essai-obs" deleted
0
```

Prometheus no longer carries any rule group. Then leave the machine and
reset the lab. `dsoxlab reset` replays the clean-up and then the lab
preparation: you get back exactly the starting state of the challenge. It
asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-reperer-les-signaux-d-un-cluster
dsoxlab check k8s-reperer-les-signaux-d-un-cluster
```

```text
╭─ Result: k8s-reperer-les-signaux-d-un-cluster ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests               │
╰────────────────────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: write the two alerts that catch a
container killed for lack of memory and a container held back by its CPU
limit, without alerting on the control Pod.

```bash
dsoxlab run k8s-reperer-les-signaux-d-un-cluster
dsoxlab challenge k8s-reperer-les-signaux-d-un-cluster
```
