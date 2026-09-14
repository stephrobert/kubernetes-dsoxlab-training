# Sortir un Deployment du CrashLoopBackOff

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétences
« Manage and evaluate container output streams » et « Troubleshoot clusters
and nodes ».

Le Pod qui redémarre en boucle est la panne la plus fréquente de l'examen, et
la plus fréquente en production. Elle se lit dans les logs, pas dans les
events.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Diagnostiquer un CrashLoopBackOff](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |

```bash
dsoxlab run   cka-troubleshoot-crashloopbackoff
dsoxlab check cka-troubleshoot-crashloopbackoff
```

Transposé de K8sExamLab le 2026-09-14, puis joué : 0 avant le travail,
100 après la solution du formateur.
