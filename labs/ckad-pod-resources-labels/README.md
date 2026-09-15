# A two-container Pod, with budgets, labels and an annotation

**CKAD** lab, *Application Design and Build* domain (20 % of the exam),
competencies "Define, build and modify container images" and "Understand
multi-container Pod design patterns".

The basic CKAD gesture, written by hand: two containers, their `resources`,
labels, an annotation. The last test reads the memory limit in the
container's cgroup, where the kernel enforces it.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Requests and Limits](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |

```bash
dsoxlab run   ckad-pod-resources-labels
dsoxlab check ckad-pod-resources-labels
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
