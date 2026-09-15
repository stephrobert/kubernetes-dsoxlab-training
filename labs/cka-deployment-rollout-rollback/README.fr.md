# Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version

Lab **CKA**, domaine *Workloads and Scheduling* (15 % de l'épreuve),
compétence « Understand application deployments and how to perform rolling
update and rollbacks ».

Le lab hérité faisait faire une mise à jour qui marche puis un retour
arrière sans raison, et lisait l'image finale. Ici le déploiement est
bloqué sur une image qui n'existe pas, comme à l'examen, et les tests
lisent les numéros de révision des ReplicaSets : ils disent si un retour
arrière a eu lieu, dans quel ordre, et si l'historique a été conservé.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Deployments Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |

```bash
dsoxlab run   cka-deployment-rollout-rollback
dsoxlab check cka-deployment-rollout-rollback
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
