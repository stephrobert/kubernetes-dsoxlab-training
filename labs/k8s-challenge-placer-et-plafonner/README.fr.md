# Placer des Pods, plafonner un namespace et dimensionner, sans guidage

Challenge du module **Scheduling et capacité** de la formation Kubernetes,
dans la section Mettre en pratique de la leçon « Ajuster les ressources d'un
Pod » : un nœud à réserver à une application, une application à placer par
affinité de nœud obligatoire et préférée, des réplicas à répartir sur
plusieurs nœuds, un namespace à plafonner et à doter de valeurs par défaut, et
une application à mettre à l'échelle sur sa charge CPU. Huit états, seuil 70,
deux bloquants.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `capacite` (Kubernetes 1.37, un control plane et trois workers) ; le lab pose le namespace `atelier` |
| Durée | environ 50 minutes |
| Page associée | [Ajuster les ressources d'un Pod, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/vertical-pod-scaling/) |

```bash
dsoxlab run    k8s-challenge-placer-et-plafonner
dsoxlab check  k8s-challenge-placer-et-plafonner
dsoxlab submit k8s-challenge-placer-et-plafonner
```
