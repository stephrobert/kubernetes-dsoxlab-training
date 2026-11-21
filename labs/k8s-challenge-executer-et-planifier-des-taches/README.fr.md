# Exécuter des tâches ponctuelles et planifiées avec Jobs et CronJobs

Challenge de la formation Kubernetes, dans la section Mettre en pratique de la
leçon « Jobs et CronJobs » : un Job indexé dont le nombre de complétions
dépend du cluster, un CronJob au planning et au fuseau imposés, une exécution
lancée à la main, et un Job en échec à réparer. Cinq exigences, seuil 80 %,
deux bloquantes.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm ; le lab pose le namespace `compta` |
| Durée | environ 40 minutes |
| Page associée | [Jobs et CronJobs, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-executer-et-planifier-des-taches
dsoxlab check  k8s-challenge-executer-et-planifier-des-taches
dsoxlab submit k8s-challenge-executer-et-planifier-des-taches
```
