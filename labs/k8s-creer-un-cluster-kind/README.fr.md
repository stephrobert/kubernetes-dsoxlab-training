# Créer un cluster kind multi-nœuds

Lab guidé du module **Fondamentaux** de la formation Kubernetes : décrire un
cluster d'un control plane et de deux workers dans un fichier de configuration
kind, puis le créer sur l'image de nœud épinglée.

| | |
|---|---|
| Cible | `k8s-kind.lab`, Docker et kind ; le lab supprime les clusters des autres labs, qui sont recréés par leur propre setup |
| Durée | environ 15 minutes |
| Page associée | [Créer votre premier cluster, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-cluster/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-creer-un-cluster-kind
dsoxlab check k8s-creer-un-cluster-kind
```
