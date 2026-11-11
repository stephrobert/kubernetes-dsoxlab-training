# Extraire des champs avec JSONPath et custom-columns

Lab guidé du module **Les ressources de base** de la formation Kubernetes :
extraire l'image du modèle d'un Deployment, puis une liste de Pods avec leur
nœud, en JSONPath et en custom-columns.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `extraction` |
| Durée | environ 15 minutes |
| Page associée | [Aide-mémoire kubectl, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-extraire-avec-kubectl
dsoxlab check k8s-extraire-avec-kubectl
```
