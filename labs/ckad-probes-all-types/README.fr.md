# Trois sondes sur un Pod : startup, liveness, readiness

Lab **CKAD**, domaine *Application Observability and Maintenance* (15 % de
l'épreuve), compétence « Implement probes and health checks ».

Le lab hérité ne vérifiait que la présence des sondes. Ici le Pod doit être
`Ready` sans redémarrage : c'est la preuve que les sondes trouvent ce
qu'elles cherchent, et une sonde vers un mauvais chemin ne passerait pas.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [Définir les Probes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/probes/) |

```bash
dsoxlab run   ckad-probes-all-types
dsoxlab check ckad-probes-all-types
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
