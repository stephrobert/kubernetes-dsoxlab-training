# Sortir un Pod de l'ImagePullBackOff

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétences
« Troubleshoot clusters and nodes » et « Manage and evaluate container output
streams ».

Une image qui ne se télécharge pas est la première panne que rencontre tout
débutant, et l'examen la pose en cinq minutes. Le message qui la résout est
dans les events, pas dans le statut.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm vanilla à un nœud |
| Durée | environ 10 minutes |
| Leçon jumelée | [Diagnostiquer un ImagePullBackOff](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/) |

```bash
dsoxlab run   cka-troubleshoot-imagepullbackoff
dsoxlab check cka-troubleshoot-imagepullbackoff
```

Transposé de K8sExamLab le 2026-09-14, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
