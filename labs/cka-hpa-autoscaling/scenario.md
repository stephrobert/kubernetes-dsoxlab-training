# Scale out automatically with a HorizontalPodAutoscaler

## The situation

In the namespace **`lab`**, the application **`php-apache`** runs with a single
replica behind the Service of the same name. Every request costs it CPU, and
the team wants it to grow on its own under load, up to ten replicas, then come
back down. The cluster has a working metrics-server: `kubectl top pods`
answers.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. A HorizontalPodAutoscaler **`php-apache-hpa`** in `lab`, in
   `autoscaling/v2`, targeting the Deployment `php-apache`, between **1** and
   **10** replicas, on a target average CPU utilization of **50 %** of the
   requests.

2. The HPA **reads metrics**: its target shows a percentage, not `<unknown>`.

3. An **observed scale-up**: under a load that you generate from a Pod in the
   cluster, the HPA took the Deployment to at least **two** replicas. The
   controller leaves a trace of it.

4. The load is **cut** at the end: no load generator Pod is still running in
   `lab`.

## Useful bearings

The HPA compares the CPU utilization of the Pods to their `requests`: with no
requests, the target stays `<unknown>` and nothing moves. It rereads the
metrics every fifteen seconds and decides every thirty; count one to two
minutes between the start of the load and the first extra Pod.
`kubectl get hpa -w` shows the transitions live, and `kubectl describe hpa` the
decisions taken.

A `wget` loop from a `busybox` Pod against the Service is enough to saturate
one replica. A Pod started for that is deleted once you are done.

## How you will know it works

The tests read the HPA, its current metrics, the events of the autoscaling
controller, and look for a load generator still running.

```bash
dsoxlab check cka-hpa-autoscaling
```
