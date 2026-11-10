# Observer la réconciliation du control plane

Lab guidé du module **Architecture** de la formation Kubernetes : supprimer un
Pod, puis un ReplicaSet, et lire quel contrôleur ramène chacun.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `architecture`, un control plane et trois workers (Kubernetes 1.37) |
| Durée | environ 20 minutes |
| Page associée | [Le control plane, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-observer-la-reconciliation
dsoxlab check k8s-observer-la-reconciliation
```
