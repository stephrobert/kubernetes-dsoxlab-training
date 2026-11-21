# Make the health of a cluster readable and write its health report

The lesson shows how to read a cluster's health: the API server's health
endpoints, `kubectl top`, what Pods reserve on each node. This course looks
at what lies behind these tools, and adds cases the lesson does not show: the
detail of `/readyz`'s checks, the kubelet's measurement read without
metrics-server, and the memory reserved per node computed by hand.

You work in a scratch namespace, `essai-sante`, with two Pods, `glouton` and
`sobre` ("greedy" and "sober"). The challenge is about another namespace: you
will do it on your own, at the end.

Related page (in French): [Observer la santé d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/observer-sante-cluster-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-observer-la-sante-d-un-cluster
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🩺 Exercise 1: the detail of the API server's checks

`/readyz` says whether the API server is ready to serve. With `?verbose`, it
details each check. Read the end of the list:

```bash
kubectl get --raw '/readyz?verbose' | tail -6
```

```text
[+]poststarthook/kube-apiserver-autoregistration ok
[+]autoregister-completion ok
[+]poststarthook/apiservice-openapi-controller ok
[+]poststarthook/apiservice-openapiv3-controller ok
[+]shutdown ok
readyz check passed
```

Each `[+]` line is a passed check, and the last line gives the verdict. A
check can also be asked for alone, or excluded:

```bash
kubectl get --raw '/readyz/etcd'; echo; kubectl get --raw '/livez?exclude=etcd' ; echo
```

```text
ok
ok
```

`/readyz/etcd` only tests access to etcd. `/livez?exclude=etcd` says whether
the process is alive without taking etcd into account. When the API answers
badly, these endpoints tell you straight away which component is at fault.

## 📏 Exercise 2: what the kubelet measures, without metrics-server

Create two Pods: `glouton` fills 48 Mi of memory, `sobre` does nothing. The
command then waits 20 seconds, the time for the kubelet to measure them:

```bash
kubectl create namespace essai-sante; kubectl run glouton --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sante -- sh -c 'dd if=/dev/zero of=/dev/shm/bloc bs=1M count=48; sleep 3600'; kubectl run sobre --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sante -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-sante --timeout=120s; sleep 20
```

```text
namespace/essai-sante created
pod/glouton created
pod/sobre created
pod/glouton condition met
pod/sobre condition met
```

The kubelet itself measures each Pod's consumption, and publishes it in a
summary that the API server can relay (`/proxy/stats/summary`). Read your two
Pods' memory in that summary:

```bash
N=$(kubectl get pod glouton -n essai-sante -o jsonpath='{.spec.nodeName}'); kubectl get --raw /api/v1/nodes/$N/proxy/stats/summary | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(p["podRef"]["name"], p["memory"]["workingSetBytes"]//1048576, "Mi") for p in d["pods"] if p["podRef"]["namespace"]=="essai-sante"]'
```

```text
glouton 48 Mi
sobre 0 Mi
```

48 Mi for `glouton`, nothing for `sobre`. This is the measurement
metrics-server collects on each node to answer `kubectl top`. On this
cluster, check whether it is registered:

```bash
kubectl get apiservice v1beta1.metrics.k8s.io -o jsonpath='{.status.conditions[0].type}={.status.conditions[0].status} ({.status.conditions[0].reason}){"\n"}'
```

```text
Error from server (NotFound): apiservices.apiregistration.k8s.io "v1beta1.metrics.k8s.io" not found
```

The Metrics API does not exist: `kubectl top` cannot answer. Making it
available is the challenge. Meanwhile, the kubelet's summary stays readable:
the measurement exists, only its relay is missing.

## 🧮 Exercise 3: the memory reserved by each node's Pods

Add up, node by node, the memory requests (`requests`) of the containers of
every running or pending Pod (`Mi demandés` means "Mi requested"):

```bash
kubectl get pods -A -o json | python3 -c '
import json,sys,collections
def mi(v):
    u={"Ki":1/1024,"Mi":1,"Gi":1024}
    for s,f in u.items():
        if v.endswith(s): return float(v[:-2])*f
    return float(v)/1048576
total=collections.Counter()
for p in json.load(sys.stdin)["items"]:
    if p["status"].get("phase") not in ("Running","Pending"): continue
    for c in p["spec"]["containers"]:
        total[p["spec"].get("nodeName","?")]+=mi(c.get("resources",{}).get("requests",{}).get("memory","0"))
for n,v in sorted(total.items()): print(n, round(v), "Mi demandés")'
```

```text
k8s-cp.lab 240 Mi demandés
k8s-w1.lab 64 Mi demandés
```

Compare with the total `kubectl describe node` shows for each node:

```bash
for n in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do printf '%s : ' $n; kubectl describe node $n | awk '/Allocated resources/{f=1} f&&/memory/{print $2, $3; exit}'; done
```

```text
k8s-cp.lab : 240Mi (6%)
k8s-w1.lab : 64Mi (2%)
```

The same figures. This total is a reservation, not a consumption: `glouton`
uses 48 Mi but requests none, and is not counted. The scheduler places Pods
according to requests, never according to consumption.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-sante
```

```text
namespace "essai-sante" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-observer-la-sante-d-un-cluster
dsoxlab check k8s-observer-la-sante-d-un-cluster
```

```text
╭─ Result: k8s-observer-la-sante-d-un-cluster ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests             │
╰──────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: make `kubectl top` available, then write a
namespace's health report.

```bash
dsoxlab run k8s-observer-la-sante-d-un-cluster
dsoxlab challenge k8s-observer-la-sante-d-un-cluster
```
