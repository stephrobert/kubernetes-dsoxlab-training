# Read what a worker Node declares

Guided lab of the **Architecture** module of the Kubernetes course: read on a
worker Node its runtime, its kubelet version, its capacity and its Ready
condition.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `architecture`, one control plane and three workers (Kubernetes 1.37) |
| Duration | about 15 minutes |
| Paired page | [Worker nodes, hands-on section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/#mettre-en-pratique) (in French) |

```bash
dsoxlab run   k8s-lire-un-node
dsoxlab check k8s-lire-un-node
```
