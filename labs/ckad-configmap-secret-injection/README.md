# Injecter configuration et secrets dans un Pod

Lab **CKAD**, domaine *Application Environment, Configuration and Security*
(25 % de l'épreuve, le plus lourd des cinq), compétences « Understand
ConfigMaps » et « Understand Secrets ».

Le geste le plus fréquent du CKAD : donner à une application sa configuration
sans la coller dans son manifeste, et ses secrets sans les écrire nulle part.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Les ConfigMaps](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/configmaps/) |

```bash
dsoxlab run   ckad-configmap-secret-injection
dsoxlab check ckad-configmap-secret-injection
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
