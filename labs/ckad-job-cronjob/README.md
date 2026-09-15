# Un Job à complétions parallèles et un CronJob

Lab **CKAD**, domaine *Application Design and Build* (20 % de l'épreuve),
compétence « Understand Jobs and CronJobs ».

Le lab hérité ne lisait que le spec du Job. Celui-ci lit aussi les
horodatages de ses Pods, pour prouver que deux exécutions ont réellement
tourné en même temps.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Les Jobs et CronJobs](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/) |

```bash
dsoxlab run   ckad-job-cronjob
dsoxlab check ckad-job-cronjob
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
