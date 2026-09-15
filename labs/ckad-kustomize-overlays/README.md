# Une base Kustomize et deux overlays, dev et prod

Lab **CKAD**, domaine *Application Deployment* (20 % de l'épreuve),
compétence « Understand and use Kustomize ».

La formation n'a pas encore de leçon sur Kustomize : la leçon jumelée est
celle des Deployments, et le trou est remonté au backlog du blog.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 20 minutes |
| Leçon jumelée | [Les Deployments](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |

```bash
dsoxlab run   ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
