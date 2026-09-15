# Reserve a node: taint, toleration and nodeSelector

**CKA** lab, *Workloads and Scheduling* domain (15 % of the exam),
placement competencies: taints, tolerations, selection by label.

The lab inherited from K8sExamLab ran on kind and checked that a Pod was
"on a worker". Here the node is named, and the last test reads what the Pod
declares: a Pod pinned with `nodeName` lands in the same place while
skipping the scheduler, and the taint with it, which the test refuses.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Advanced scheduling: Affinity, Taints, Tolerations](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |

```bash
dsoxlab run   cka-taints-tolerations-placement
dsoxlab check cka-taints-tolerations-placement
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
