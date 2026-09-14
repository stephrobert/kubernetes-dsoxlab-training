# Entrer dans un conteneur sans shell avec kubectl debug

Lab **CKA**, domaine *Troubleshooting* (30 % de l'épreuve), compétences
« Troubleshoot clusters and nodes » et « Manage and evaluate container output
streams ».

Les images distroless n'ont ni shell ni outils, et `kubectl exec` y échoue.
L'examen attend qu'on sache y entrer quand même, et qu'on sache atteindre un
nœud sans session SSH.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Débugger une application](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |

```bash
dsoxlab run   cka-kubectl-debug
dsoxlab check cka-kubectl-debug
```

Transposé de K8sExamLab le 2026-09-14, puis joué : 0 avant le travail,
100 après la solution du formateur.
