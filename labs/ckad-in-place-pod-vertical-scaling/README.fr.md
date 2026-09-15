# Redimensionner un Pod en place, sans le redémarrer

Lab **CKAD**, domaine *Application Environment, Configuration and Security*
(25 % de l'épreuve), compétence « Understand requests, limits, quotas ».

Le redimensionnement en place est activé par défaut depuis la 1.33. Le lab
prouve les deux choses qui comptent : le Pod est resté le même objet, et le
noyau applique la nouvelle limite.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [Requests et Limits](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |

```bash
dsoxlab run   ckad-in-place-pod-vertical-scaling
dsoxlab check ckad-in-place-pod-vertical-scaling
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
