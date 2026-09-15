# Grant read-only access to Pods with RBAC

**CKAD** lab, *Application Environment, Configuration and Security* domain
(25 % of the exam), competency "Understand authentication, authorization
and admission control".

RBAC is measured with `kubectl auth can-i --as`, and a lab that only checks
the rights granted would let a `cluster-admin` through. This one checks both
sides.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Kubernetes RBAC](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |

```bash
dsoxlab run   ckad-rbac-role-rolebinding
dsoxlab check ckad-rbac-role-rolebinding
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
