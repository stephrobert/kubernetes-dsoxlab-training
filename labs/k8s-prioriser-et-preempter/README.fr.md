# Prioriser des Pods et observer une préemption

Lab guidé de la leçon « Scheduling avancé », module 8 de la formation
Kubernetes : deux PriorityClass, un worker rempli de Pods de basse priorité,
puis un Pod urgent de haute priorité qui en fait préempter un.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `multi` (un control plane, deux workers) ; le lab pose le namespace `ordonnancement` |
| Durée | environ 25 minutes |
| Page associée | [Scheduling avancé, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/scheduling-avance/#mettre-en-pratique) |

Sur kind, chaque nœud annonce tous les CPU de l'hôte : le setup calcule le
remplissage sur l'allocatable réel du worker. Le `cleanup.yaml` retire le
namespace et les PriorityClass, qui sont des objets du cluster.

```bash
dsoxlab run   k8s-prioriser-et-preempter
dsoxlab check k8s-prioriser-et-preempter
```
