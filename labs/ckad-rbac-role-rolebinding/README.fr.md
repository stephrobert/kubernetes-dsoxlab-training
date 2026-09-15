# Donner un accès en lecture seule aux Pods avec RBAC

Lab **CKAD**, domaine *Application Environment, Configuration and Security*
(25 % de l'épreuve), compétence « Understand authentication, authorization
and admission control ».

Le RBAC se mesure avec `kubectl auth can-i --as`, et un lab qui ne vérifie
que les droits accordés laisserait passer un `cluster-admin`. Celui-ci
vérifie les deux côtés.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [RBAC Kubernetes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |

```bash
dsoxlab run   ckad-rbac-role-rolebinding
dsoxlab check ckad-rbac-role-rolebinding
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
