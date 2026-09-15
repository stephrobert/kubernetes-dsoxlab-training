# Give an application an identity: ServiceAccount, Role, RoleBinding

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain
(25 % of the exam), competency "Manage role based access control (RBAC)".

The lab inherited from K8sExamLab had the candidate create everything and
checked the rights with `kubectl auth can-i`. Here the application exists
and does not start, for want of an identity; once the rights are in place,
the proof comes from the Pod itself, which queries the API with its
projected token: listing answers 200, while deleting, reading Secrets or
looking into another namespace answer 403.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [ServiceAccounts for developers](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/) |

```bash
dsoxlab run   cka-rbac-serviceaccount
dsoxlab check cka-rbac-serviceaccount
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
