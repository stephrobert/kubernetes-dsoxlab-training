# Extract fields with JSONPath and custom-columns

Guided lab of the **Les ressources de base** module of the Kubernetes course:
extract the image of the template of a Deployment, then a list of Pods with
their node, with JSONPath and with custom-columns.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), namespace `extraction` |
| Duration | about 15 minutes |
| Related page | [Aide-mémoire kubectl, section Mettre en pratique](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-cheat-sheet/) |

```bash
dsoxlab run   k8s-extraire-avec-kubectl
dsoxlab check k8s-extraire-avec-kubectl
```
