# Diagnostiquer deux Pods en échec

Lab guidé du module **Les ressources de base** de la formation Kubernetes : lire
la cause de deux pannes de Pod, une image introuvable et un conteneur qui sort
en erreur, puis réparer chaque Pod du geste juste.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `pods-en-panne` |
| Durée | environ 20 minutes |
| Page associée | [Pods, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pods/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-diagnostiquer-un-pod
dsoxlab check k8s-diagnostiquer-un-pod
```
