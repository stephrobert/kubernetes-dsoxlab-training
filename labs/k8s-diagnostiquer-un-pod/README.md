# Diagnose two failing Pods

Guided lab of the **Les ressources de base** module of the Kubernetes course:
read the cause of two Pod failures, an image that cannot be found and a
container that exits with an error, then repair each Pod with the right gesture.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `pods-en-panne` |
| Duration | about 20 minutes |
| Related page | [Pods, section Mettre en pratique](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/pods/) |

```bash
dsoxlab run   k8s-diagnostiquer-un-pod
dsoxlab check k8s-diagnostiquer-un-pod
```
