# Étiqueter et sélectionner des Pods

Lab guidé du module **Les ressources de base** de la formation Kubernetes :
poser un label qui survit au remplacement des Pods, décrire un Deployment par
une annotation, et écrire un sélecteur à négation qui rend exactement les Pods
voulus.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `etiquettes` |
| Durée | environ 15 minutes |
| Page associée | [Labels et annotations, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-label-annotate/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-labels-et-selecteurs
dsoxlab check k8s-labels-et-selecteurs
```
