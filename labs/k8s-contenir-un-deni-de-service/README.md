# Contain a denial of service inside its namespace

The lesson shows how a Pod without limits can exhaust a cluster, and how
quotas contain it. This course adds cases the lesson does not show: CPU
throttling read directly in the container's cgroup, a temporary disk limit
that gets the Pod evicted, and a floor that refuses a container that is too
small.

You work in a scratch namespace, `essai-dos`. The challenge is about other
namespaces: you will do it on your own, at the end.

Related page (in French): [Déni de service : épuiser un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/deni-de-service-cluster/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-contenir-un-deni-de-service
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🐢 Exercise 1: a throttled CPU

Start a Pod that computes non-stop, limited to 10 thousandths of a CPU
(`frein` means "brake"):

```bash
kubectl create namespace essai-dos; kubectl run frein --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dos --overrides='{"spec":{"containers":[{"name":"frein","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","while :; do :; done"],"resources":{"limits":{"cpu":"100m"}}}]}}' -- true; kubectl wait --for=condition=Ready pod/frein -n essai-dos --timeout=60s; sleep 20
```

```text
namespace/essai-dos created
pod/frein created
pod/frein condition met
```

A CPU limit does not kill the container: it **throttles** it. The kernel shows
it in the container's cgroup:

```bash
kubectl exec frein -n essai-dos -- cat /sys/fs/cgroup/cpu.max; kubectl exec frein -n essai-dos -- grep -E 'nr_periods|nr_throttled' /sys/fs/cgroup/cpu.stat
```

```text
10000 100000
nr_periods 202
nr_throttled 202
```

`cpu.max` is `10000 100000`: 10 ms of computing allowed per 100 ms period.
`nr_throttled` equals `nr_periods`: the container was throttled in every
period. It runs, but slowly, and that is what protects its neighbours.

```bash
kubectl top pod frein -n essai-dos 2>&1 | tail -1
```

```text
error: Metrics API not available
```

`kubectl top` does not answer: this cluster has no metrics-server. Reading the
cgroup works everywhere.

## 💾 Exercise 2: a capped temporary disk

A container's temporary disk (its files outside volumes) is limited like
memory. Start a Pod limited to 50Mi that writes 80Mi (`disque-plein` means
"full disk"):

```bash
kubectl run disque-plein --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dos --overrides='{"spec":{"containers":[{"name":"d","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","dd if=/dev/zero of=/tmp/gros bs=1M count=80; sleep 3600"],"resources":{"limits":{"ephemeral-storage":"50Mi"}}}]}}' -- true; sleep 60; kubectl get pod disque-plein -n essai-dos; kubectl get pod disque-plein -n essai-dos -o jsonpath='{.status.reason}: {.status.message}{"\n"}'
```

```text
pod/disque-plein created
NAME           READY   STATUS   RESTARTS   AGE
disque-plein   0/1     Error    0          60s
Evicted: Pod ephemeral local storage usage exceeds the total limit of containers 50Mi. 
```

The kubelet **evicted** the Pod as soon as it went over its limit, with a
message that gives the cause. Without this limit, a single Pod could fill the
node's disk and bring down all the others.

## 📏 Exercise 3: a floor for every container

A LimitRange can also set a **minimum**. Set a floor of 50m of CPU and 32Mi of
memory, then try a smaller container (`plancher` means "floor", `minuscule`
"tiny"):

```bash
cat <<'YAML' | kubectl apply -n essai-dos -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: plancher
spec:
  limits:
    - type: Container
      min: {cpu: 50m, memory: 32Mi}
YAML
kubectl run minuscule --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dos --overrides='{"spec":{"containers":[{"name":"m","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"10m","memory":"8Mi"},"limits":{"cpu":"10m","memory":"8Mi"}}}]}}' -- true
```

```text
limitrange/plancher created
Error from server (Forbidden): pods "minuscule" is forbidden: [minimum memory usage per Container is 32Mi, but request is 8Mi, minimum cpu usage per Container is 50m, but request is 10m]
```

Refused at creation, with both reasons. A floor stops anyone from slipping
under a quota's radar with a crowd of tiny containers.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-dos
```

```text
namespace "essai-dos" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-contenir-un-deni-de-service
dsoxlab check k8s-contenir-un-deni-de-service
```

```text
╭─ Result: k8s-contenir-un-deni-de-service ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests          │
╰───────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a sandbox namespace to cap, and a greedy
application to bound without starving its neighbour.

```bash
dsoxlab run k8s-contenir-un-deni-de-service
dsoxlab challenge k8s-contenir-un-deni-de-service
```
