# Apply a VPA recommendation

## The situation

In the **`dimensionnement`** namespace, the **`catalogue`** Deployment runs two
replicas with requests picked at random: **5m** of CPU and **16Mi** of memory,
under a CPU limit of **50m**. The team wants requests based on actual usage,
without letting an automaton restart its Pods.

The kubeadm cluster already runs **metrics-server** and the **Vertical Pod
Autoscaler** 1.8.1. You are on the control plane, with `kubectl` configured.

## What you must achieve

1. A VerticalPodAutoscaler **`catalogue`**, in `dimensionnement`, targeting the
   `catalogue` Deployment in **`Off`** mode: it recommends, it does not act.
2. That VPA has produced a **recommendation** for the `catalogue` container.
3. The Deployment's **requests** fit: **CPU** between the **lower bound**
   (`lowerBound`) and the **upper bound** (`upperBound`) of that
   recommendation; **memory** at least the **usage metrics-server measures**,
   and at most the upper bound.
4. The running Pods carry these requests.
5. The VPA has **evicted no Pod**.

## Useful bearings

The recommender reads metrics every minute: the first recommendation comes a
few minutes after the VPA is created. `kubectl describe vpa` shows it,
container by container.

The target (`target`) is not a value to copy blindly. The recommender never
goes below a **250Mi floor** of memory per Pod, even for a container that uses
less: its memory lower bound is only that floor. `kubectl top pods` tells what
the container really uses, and memory is set on that measure, with a margin.

A **CPU limit that is too low** caps the measured usage, hence the CPU target:
raising a request above the limit is refused by the API. Choose a CPU value
between the two bounds, consistent with the limit.

A VPA in any mode other than `Off` evicts Pods to give them its values: that is
exactly what the team refuses here.

## How you will know it works

The tests read the VPA and its recommendation at check time, then compare the
requests of the Deployment and of the running Pods with its bounds and with the
usage metrics-server measures. Finally they
look for a trace of an eviction by the VPA in the namespace.

```bash
dsoxlab check k8s-appliquer-une-recommandation-vpa
```
