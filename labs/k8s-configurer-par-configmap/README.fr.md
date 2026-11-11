# Configurer une application par ConfigMap

Lab guidé du module **Les ressources de base** de la formation Kubernetes :
injecter des valeurs d'un ConfigMap en variables et un fichier d'un autre par
un volume, modifier les deux, et constater ce que seul un redémarrage
rafraîchit.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `configuration` |
| Durée | environ 20 minutes |
| Page associée | [ConfigMaps, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/configmaps/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-configurer-par-configmap
dsoxlab check k8s-configurer-par-configmap
```
