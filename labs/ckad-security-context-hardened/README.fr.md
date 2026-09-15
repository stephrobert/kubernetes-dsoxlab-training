# Durcir un Pod avec un securityContext

Lab **CKAD**, domaine *Application Environment, Configuration and Security*
(25 % de l'épreuve), compétence « Understand SecurityContexts ».

Durcir un Pod est facile ; le faire tourner durci l'est moins. Ce lab exige
les deux : le confinement agit, et l'application sert.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Security Context](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |

```bash
dsoxlab run   ckad-security-context-hardened
dsoxlab check ckad-security-context-hardened
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
