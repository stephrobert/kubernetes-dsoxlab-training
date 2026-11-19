# Challenge: Label a node, show its role and reserve it for one team

## The situation

The kubeadm cluster has three nodes: the control plane `k8s-cp.lab` and two
workers, `k8s-w1.lab` and `k8s-w2.lab`. The **data team** takes over the worker
**`k8s-w2.lab`**: its jobs will have the node to themselves.

In the namespace **`equipes`**, two applications already run, or would like
to:

- **`rapports`** belongs to another team. Its two replicas are spread over
  `k8s-w1.lab` and `k8s-w2.lab`.
- **`entrepot`** is the data team's application. It requires a node labelled
  for its team and already tolerates the reservation you are going to set. It
  stays **Pending** as long as no node carries that label.

You are on the control plane, with `kubectl` configured, as root.

## What you must achieve

1. `k8s-w2.lab`, and **no other** node, carries the label **`equipe=data`**.
2. The **ROLES** column of `kubectl get nodes` shows the role **`data`** for
   `k8s-w2.lab`.
3. The node carries the annotation **`maintenance-contact=data@formation.test`**.
4. The node is **reserved** for the data team by a taint of key `equipe` and
   value `data`: the other teams' Pods **already installed** on the node must
   leave it, and not come back.
5. `entrepot` runs on `k8s-w2.lab`, and `rapports` still runs with its two
   replicas, **elsewhere**.

## Landmarks

A label is set on a running node, without restarting it: it only changes the
placement decisions to come. The ROLES column reads the
`node-role.kubernetes.io/<role>` labels, whose value is empty by convention;
they improve readability, they place nothing.

A taint repels the Pods that do not tolerate it. The whole question is the
**effect**: two of the three effects only act on the Pods to come, the third
also evicts the ones already there. Isolating a node moves the other teams'
Pods, it must not stop them.

## How you will know it works

The tests read the labels, the annotation and the taints of the nodes, then
look where the Pods of both applications run.

```bash
dsoxlab check cka-etiqueter-et-isoler-un-noeud
```
