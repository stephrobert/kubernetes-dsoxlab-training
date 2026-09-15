# Get a Deployment out of CrashLoopBackOff

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competencies
"Manage and evaluate container output streams" and "Troubleshoot clusters
and nodes".

The Pod that restarts in a loop is the most frequent failure in the exam, and
the most frequent one in production. It is read in the logs, not in the
events.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Diagnosing a CrashLoopBackOff](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |

```bash
dsoxlab run   cka-troubleshoot-crashloopbackoff
dsoxlab check cka-troubleshoot-crashloopbackoff
```

Ported from K8sExamLab on 2026-09-14, then played: 0 before the work,
100 after the trainer's solution.
