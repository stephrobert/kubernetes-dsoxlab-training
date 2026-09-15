# Un Pod bloqué par un ConfigMap qui n'existe pas

Lab **CKAD**, domaine *Application Observability and Maintenance* (15 % de
l'épreuve), compétence « Debugging in Kubernetes ».

La panne sans logs : le conteneur n'existe pas encore, et seuls les events
parlent. Le lab hérité vérifiait que le ConfigMap existe ; ici l'application
doit servir ce qu'il contient.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [Débugger une application](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |

```bash
dsoxlab run   ckad-troubleshoot-missing-configmap
dsoxlab check ckad-troubleshoot-missing-configmap
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
