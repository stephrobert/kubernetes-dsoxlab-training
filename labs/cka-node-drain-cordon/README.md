# Drain a worker for maintenance, without cutting the service

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain
(25 % of the exam), competencies "Prepare underlying infrastructure" and
"Manage the lifecycle of Kubernetes clusters".

The lab inherited from K8sExamLab ran on kind and read specs: a PDB existed,
nodes were schedulable. Here the worker is a real machine, the CNI runs on
it as a DaemonSet, an orphan Pod is lying around, and the tests prove that
every Pod of the application was recreated elsewhere after the lab started.

| | |
|---|---|
| Targets | `k8s-cp.lab`, and `k8s-w1.lab` reachable over `ssh` from the control plane |
| Duration | about 15 minutes |
| Companion lesson | [Preparing a Kubernetes cluster maintenance](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/) |

```bash
dsoxlab run   cka-node-drain-cordon
dsoxlab check cka-node-drain-cordon
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
