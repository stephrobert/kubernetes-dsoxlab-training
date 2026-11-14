# Label and select Pods

Guided lab of the **Les ressources de base** module of the Kubernetes course:
put a label that survives the replacement of the Pods, describe a Deployment
with an annotation, and write a selector with a negation that returns exactly
the wanted Pods.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `etiquettes` |
| Duration | about 15 minutes |
| Related page | [Labels and annotations, section Mettre en pratique](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-label-and-annotate/) |

```bash
dsoxlab run   k8s-labels-et-selecteurs
dsoxlab check k8s-labels-et-selecteurs
```
