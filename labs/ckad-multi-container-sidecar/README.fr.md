# Un sidecar natif qui suit les logs de l'application

Lab **CKAD**, domaine *Application Design and Build* (20 % de l'épreuve),
compétence « Understand multi-container Pod design patterns ».

Le sidecar natif, init container à `restartPolicy: Always`, est stable
depuis la 1.33 : c'est la forme que l'examen attend, et ce lab refuse le
second conteneur ordinaire qui la remplaçait avant.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Init Containers et Sidecars](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/init-containers-sidecars/) |

```bash
dsoxlab run   ckad-multi-container-sidecar
dsoxlab check ckad-multi-container-sidecar
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
