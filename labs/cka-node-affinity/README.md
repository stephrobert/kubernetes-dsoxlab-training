# Placing with nodeAffinity: required constraint and preference

**CKA** lab, *Workloads and Scheduling* domain (15 % of the exam),
placement competencies: required and preferred `nodeAffinity`.

The lab inherited from K8sExamLab required `kubernetes.io/os=linux`, a
constraint every node satisfies, so it measured nothing. Here the required
rule bears on a label only the worker has, and all three Pods must land
there; the `gpu-app` Pod must have waited for its label, which the
`PodScheduled` condition tells.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Advanced scheduling: Affinity, Taints, Tolerations](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/affinity-toleration-taint/) |

```bash
dsoxlab run   cka-node-affinity
dsoxlab check cka-node-affinity
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
