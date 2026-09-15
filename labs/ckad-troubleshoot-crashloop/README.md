# Three Pods in CrashLoopBackOff, three causes

**CKAD** lab, *Application Observability and Maintenance* domain (15 % of
the exam), competencies "Utilize container logs" and "Debugging in
Kubernetes".

Three different readings for three failures: the container's exit message,
its previous logs, and the `OOMKilled` reason that only the kubelet tells.
Each test watches the Pod for fifteen seconds: a Pod that is `Running`
between two deaths does not pass.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Diagnosing a CrashLoopBackOff](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/) |

```bash
dsoxlab run   ckad-troubleshoot-crashloop
dsoxlab check ckad-troubleshoot-crashloop
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
