# Un Pod à deux conteneurs, avec budgets, labels et annotation

Lab **CKAD**, domaine *Application Design and Build* (20 % de l'épreuve),
compétences « Define, build and modify container images » et « Understand
multi-container Pod design patterns ».

Le geste de base du CKAD, écrit à la main : deux conteneurs, leurs
`resources`, des labels, une annotation. Le dernier test lit la limite de
mémoire dans le cgroup du conteneur, là où le noyau l'applique.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [Requests et Limits](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |

```bash
dsoxlab run   ckad-pod-resources-labels
dsoxlab check ckad-pod-resources-labels
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
