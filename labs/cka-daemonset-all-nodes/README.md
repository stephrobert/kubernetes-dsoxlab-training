# An agent on every node, including the control plane

**CKA** lab, *Workloads and Scheduling* domain (15 % of the exam),
competency "Understand the primitives used to create robust, self-healing,
application deployments", here the DaemonSet and tolerations.

The catalogue's shared base removes the control plane taint to leave room for
single-node labs. This lab puts it back for the length of the session, and the
tests require that it stays: the agent must run there through a toleration, not
because the control plane was opened to everyone.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Kubernetes DaemonSets](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/daemonsets/) |

```bash
dsoxlab run   cka-daemonset-all-nodes
dsoxlab check cka-daemonset-all-nodes
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
