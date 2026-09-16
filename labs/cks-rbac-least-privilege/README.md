# Take cluster-admin back from a service account, without stopping its work

**CKS** lab, *Cluster Hardening* domain (15 % of the exam), competencies "Use
Role Based Access Controls to minimize exposure" and "Exercise caution in
using service accounts".

The catalogue already has two RBAC labs, one CKA and one CKAD, which teach how
to **grant** a permission. This one teaches how to **take one back** without
breaking the application, which is the CKS gesture and the harder of the two:
nobody complains about an over-broad permission until something leaks.

The tests do not read manifests, save one and for a precise reason: a
permission cannot be deduced from a file. Rules add up, a binding forgotten
elsewhere can reopen everything, and an object's name says nothing about what
it grants. So they put the questions to the API server with `kubectl auth
can-i --as`, and require **both directions**: what the account must be able to
do, and what it must no longer be able to do.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [RBAC](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/) |

```bash
dsoxlab run   cks-rbac-least-privilege
dsoxlab check cks-rbac-least-privilege
```

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
