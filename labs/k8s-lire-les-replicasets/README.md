# Trace a Pod back to its Deployment

Guided lab of the **Les ressources de base** module of the Kubernetes course:
read the ReplicaSets of an updated Deployment, find in the events of a
ReplicaSet why a Deployment creates no Pod, then repair it.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `replicasets` |
| Duration | about 20 minutes |
| Related page | [ReplicaSets, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/replicasets/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-lire-les-replicasets
dsoxlab check k8s-lire-les-replicasets
```
