# Place a static Pod on a worker, without going through the API

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain
(25 % of the exam), competency "Understand the role of the kubelet".

The lab inherited from K8sExamLab had no runnable solution: its file was
truncated. Here the candidate looks for the watched directory in the worker
kubelet's own configuration, and the last test asks the node's runtime whether
it is really running the container.

| | |
|---|---|
| Targets | `k8s-cp.lab`, and `k8s-w1.lab` reachable over `ssh` from the control plane |
| Duration | about 10 minutes |
| Companion lesson | [How worker nodes work](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |

```bash
dsoxlab run   cka-static-pod
dsoxlab check cka-static-pod
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
