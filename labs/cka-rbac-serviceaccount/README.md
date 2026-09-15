# Donner une identité à une application : ServiceAccount, Role, RoleBinding

Lab **CKA**, domaine *Cluster Architecture, Installation and Configuration*
(25 % de l'épreuve), compétence « Manage role based access control (RBAC) ».

Le lab hérité faisait tout créer par le candidat et vérifiait les droits
avec `kubectl auth can-i`. Ici l'application existe et ne démarre pas, faute
d'identité ; une fois les droits posés, la preuve vient du Pod lui-même,
qui interroge l'API avec son jeton projeté : lister répond 200, supprimer,
lire les Secrets ou regarder un autre namespace répondent 403.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Leçon jumelée | [ServiceAccounts pour développeurs](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/) |

```bash
dsoxlab run   cka-rbac-serviceaccount
dsoxlab check cka-rbac-serviceaccount
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
