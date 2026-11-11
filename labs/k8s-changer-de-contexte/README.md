# Merge a kubeconfig and switch context

Guided lab of the **Fondamentaux** module of the Kubernetes course: store and
protect a received kubeconfig, merge it without overwriting your own, rename
its context, switch to it and set its default namespace.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind clusters `boutique` (starting context) and `lab` (the "received" cluster) |
| Duration | about 20 minutes |
| Related page | [Kubeconfig et contextes, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-contexte/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-changer-de-contexte
dsoxlab check k8s-changer-de-contexte
```
