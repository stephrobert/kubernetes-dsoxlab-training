# Donner une identité stable à chaque réplica avec un StatefulSet

Lab guidé de la leçon « Les StatefulSets » du module **Workloads avancés** de la
formation Kubernetes : remplacer un Deployment sans identité par un StatefulSet
derrière un Service headless, avec un volume par réplica, et prouver qu'une
donnée survit à son Pod.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose l'annuaire en Deployment dans le namespace `identites` |
| Durée | environ 30 minutes |
| Page associée | [Les StatefulSets, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/statefulsets/#mettre-en-pratique) |

```bash
dsoxlab run   cka-statefulset-identite-stable
dsoxlab check cka-statefulset-identite-stable
```
