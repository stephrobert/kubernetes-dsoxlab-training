# Resize a Pod in place, without restarting it

**CKAD** lab, *Application Environment, Configuration and Security* domain
(25 % of the exam), competency "Understand requests, limits, quotas".

In-place resizing has been enabled by default since 1.33. The lab proves the
two things that matter: the Pod stayed the same object, and the kernel applies
the new limit.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Requests and Limits](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/) |

```bash
dsoxlab run   ckad-in-place-pod-vertical-scaling
dsoxlab check ckad-in-place-pod-vertical-scaling
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
