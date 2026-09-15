# Roll back a stuck rollout, then ship the right version

**CKA** lab, *Workloads and Scheduling* domain (15 % of the exam),
competency "Understand application deployments and how to perform rolling
update and rollbacks".

The inherited lab had you run an update that works, then roll it back for no
reason, and it read the final image. Here the rollout is stuck on an image that
does not exist, as in the exam, and the tests read the revision numbers of the
ReplicaSets: they say whether a rollback took place, in what order, and whether
the history was kept.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Kubernetes Deployments](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |

```bash
dsoxlab run   cka-deployment-rollout-rollback
dsoxlab check cka-deployment-rollout-rollback
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
