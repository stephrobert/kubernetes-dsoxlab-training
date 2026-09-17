# Basculer le trafic d'une version à l'autre : blue-green

Lab **CKAD**, domaine *Application Deployment* (20 % de l'épreuve),
compétence « Use Kubernetes primitives to implement common deployment
strategies (blue/green or canary) ».

Le lab hérité vérifiait le selector du Service sans jamais faire de
requête. Ici chaque version répond son nom, et six requêtes depuis un client
doivent toutes répondre `green`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Rolling Updates et Rollbacks](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

```bash
dsoxlab run   ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
