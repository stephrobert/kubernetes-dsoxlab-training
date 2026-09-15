# Régler une mise à jour progressive : maxSurge et maxUnavailable

Lab **CKAD**, domaine *Application Deployment* (20 % de l'épreuve),
compétence « Understand Deployments and how to perform rolling updates ».

Le lab hérité demandait un ConfigMap « evidence » recopiant les valeurs :
il ne prouvait rien. Ici la preuve est dans les ReplicaSets, l'ancien à
zéro, le nouveau au complet.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Rolling Updates et Rollbacks](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

```bash
dsoxlab run   ckad-rolling-update-strategy
dsoxlab check ckad-rolling-update-strategy
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
