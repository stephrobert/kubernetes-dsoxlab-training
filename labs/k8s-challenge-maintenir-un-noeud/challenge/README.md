# Challenge: Drain, maintain and bring a node back into service, then upgrade the cluster

## The situation

The kubeadm cluster runs **1.36.4**, one minor version behind. In the
**`maintenance`** namespace, the **`catalogue`** application serves with
**four replicas**, spread over the control plane and the worker. A diagnostic
tool, the **`outil-diag`** Pod, lingers on the worker with no controller; the
team will not miss it.

Tonight's schedule:

- the worker **`k8s-w1.lab`** goes down for hardware maintenance, then comes
  back;
- then the whole cluster goes up to **1.37.0**;
- and at no time may `catalogue` drop below **two available replicas**.

In the middle of the night, the catalogue team also asks to raise
**`MAX_CONNEXIONS`** in its configuration (the **`catalogue-config`**
ConfigMap) from `50` to **`200`**, right away. Its manifests live in the git
repository **`~/maintenance`**, and that repository is what counts at the next
deployment.

You are on **`k8s-cp.lab`**, the control plane, with `kubectl` configured and
`sudo` rights. `ssh k8s-w1.lab` opens a session on the worker, where you also
have `sudo`. No procedure is given: the module taught you what you need.

## What you must achieve

1. A **PodDisruptionBudget** named **`catalogue-pdb`** guarantees **at least
   two** available Pods of `catalogue`, and really targets its Pods.
2. The worker was **emptied**: the `catalogue` Pods it carried were recreated
   elsewhere, `outil-diag` is gone, and the network DaemonSet **stayed** on it.
3. The worker is **back in service**: it accepts Pods again.
4. A **`drain-evidence`** ConfigMap, in `maintenance`, records the operation:
   the **`drained-node`** key names the drained node, the **`status`** key is
   **`completed`**.
5. The **API server** reports version **1.37.0**.
6. **Every node** reports **1.37.0**, **none** was left unschedulable, and
   `catalogue` has **its four replicas ready**.
7. In the cluster, `MAX_CONNEXIONS` is **`200`**, and the **last commit** of
   the `~/maintenance` repository carries **the same value**.

## How you are graded

Seven states, equal weight. The threshold is **70 out of 100**, and states
**2 and 6** are **blocking**: the emptied worker, and the whole cluster
upgraded without losing the application. Passing the others does not make up
for missing one of them.

The tests read the state of the cluster and the git repository, never the
commands typed. For state 3, the grader starts a short-lived Pod,
`sonde-placement`, that the scheduler must place on the worker, then removes
it. The feedback is limited to the list of unmet criteria, by their label, and the score: no message says why.

```bash
dsoxlab check  k8s-challenge-maintenir-un-noeud
dsoxlab submit k8s-challenge-maintenir-un-noeud
```
