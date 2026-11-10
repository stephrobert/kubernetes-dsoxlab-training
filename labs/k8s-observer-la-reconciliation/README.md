# Watch the control plane reconcile

Guided lab of the **Architecture** module of the Kubernetes course: delete a
Pod, then a ReplicaSet, and read which controller brings each one back.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `architecture`, one control plane and three workers (Kubernetes 1.37) |
| Duration | about 20 minutes |
| Paired page | [The control plane, hands-on section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/#mettre-en-pratique) (in French) |

```bash
dsoxlab run   k8s-observer-la-reconciliation
dsoxlab check k8s-observer-la-reconciliation
```
