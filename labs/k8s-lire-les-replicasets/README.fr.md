# Remonter d'un Pod à son Deployment

Lab guidé du module **Les ressources de base** de la formation Kubernetes : lire
les ReplicaSets d'un Deployment mis à jour, trouver dans les événements d'un
ReplicaSet pourquoi un Deployment ne crée aucun Pod, puis le réparer.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), namespace `replicasets` |
| Durée | environ 20 minutes |
| Page associée | [ReplicaSets, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/replicasets/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-lire-les-replicasets
dsoxlab check k8s-lire-les-replicasets
```
