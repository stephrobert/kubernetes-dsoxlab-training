# Détecter et migrer les API retirées

Lab guidé de la leçon « Gérer les dépréciations d'API », module Administrer le
cluster du niveau 4 : six manifestes hérités, dont quatre en API retirée
(PodDisruptionBudget, HorizontalPodAutoscaler, CronJob, Ingress), à repérer, migrer
sans rien changer à ce qu'ils décrivent, et appliquer.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose le namespace `migration` |
| Durée | environ 30 minutes |
| Page associée | [Dépréciations d'API, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/api-deprecations/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-detecter-les-api-depreciees
dsoxlab check k8s-detecter-les-api-depreciees
```
