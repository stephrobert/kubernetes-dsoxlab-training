# Challenge: Make the health of a cluster readable and write its health report

## The situation

You are given a three-node kubeadm cluster for the day. Before touching
anything, the team wants a **health report**. Problem: `kubectl top` answers
nothing, because **metrics-server is not installed**.

Its official manifest, pinned in **version 0.9.0**, is waiting for you in
**`~/sante/metrics-server-v0.9.0.yaml`**. The namespace **`sante`** carries the
Pods to watch.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. **`kubectl top nodes` answers**: the Metrics API (`v1beta1.metrics.k8s.io`)
   is available.
2. A ConfigMap **`bulletin`** in the namespace `sante` carries two keys:
   - **`pod-le-plus-gourmand`**: the name of the Pod of `sante` that uses the
     most **memory**, as `kubectl top` measures it;
   - **`noeud-le-plus-reserve`**: the name of the node whose **allocatable CPU
     is the most reserved by the requests** of the Pods running on it.

## Landmarks

On a kubeadm cluster, the kubelets serve self-signed certificates.
metrics-server refuses them by default: the Metrics API then stays unavailable
and `kubectl top` answers `Metrics API not available`. In a lab, the option
`--kubelet-insecure-tls` lifts this refusal; in production, you sign the
kubelets' certificates.

Two measures do not say the same thing. `kubectl top` shows the **current
usage**. The `Allocated resources` section of `kubectl describe node` shows
what is **reserved** by requests, whether the Pod uses it or not. The scheduler
decides on this reservation.

The memory-hungry Pod changes at each `dsoxlab run`: measure, do not guess.

## How you will know it works

The tests query the Metrics API and the APIService, compute the most
memory-hungry Pod and the most reserved node themselves, then compare with your
report.

```bash
dsoxlab check k8s-observer-la-sante-d-un-cluster
```
