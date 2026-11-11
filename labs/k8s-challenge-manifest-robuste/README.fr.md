# Livrer un manifeste robuste à partir d'un cahier des charges

Challenge du module **Déployer ses applications** de la formation Kubernetes,
dans la section Mettre en pratique de la leçon « Débugger une application » :
une application livrée par Kustomize en deux variantes, avec init container,
sidecar natif, budgets et sondes, un CronJob, un Job, et un Pod en panne à
diagnostiquer avant de le réparer. Dix exigences, seuil 70, trois bloquantes.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose le namespace `expedition` et un Pod en panne |
| Durée | environ 60 minutes |
| Page associée | [Débugger une application, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-manifest-robuste
dsoxlab check  k8s-challenge-manifest-robuste
dsoxlab submit k8s-challenge-manifest-robuste
```
