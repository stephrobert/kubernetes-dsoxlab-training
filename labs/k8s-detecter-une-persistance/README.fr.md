# Repérer et retirer ce qu'un attaquant a laissé derrière lui

Lab guidé de la leçon « Persistance : ce qu'un attaquant laisse derrière lui »,
module Modèle de menaces et cadres de la formation Kubernetes (niveau 5,
objectif KCSA « Persistence »). Une charge planifiée recrée chaque minute
l'accès d'un attaquant : la repérer en listant ce qui est planifié, qui a quels
droits et ce que disent les événements, la consigner, la retirer sans toucher à
l'application légitime, et prouver que l'accès ne revient pas.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose le namespace `facturation` et trois objets de l'attaquant à l'échelle du cluster |
| Durée | environ 30 minutes |
| Page associée | [Persistance : ce qu'un attaquant laisse derrière lui](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/persistance-attaquant-cluster/) |

La méthode est dans `scenario.fr.md` : lister les objets planifiés, les droits
et les webhooks, lire les événements et, quand l'API server en écrit un, le
journal d'audit.

Le `cleanup.yaml` supprime d'abord le CronJob de l'attaquant, pour qu'aucun
passage en cours ne recrée l'accès, puis le namespace, puis les
ClusterRoleBindings et le ClusterRole laissés par l'attaquant, et le fichier
de constat sur le nœud.

```bash
dsoxlab run   k8s-detecter-une-persistance
dsoxlab check k8s-detecter-une-persistance
```
