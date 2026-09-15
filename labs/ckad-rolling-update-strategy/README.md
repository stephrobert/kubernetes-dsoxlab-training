# Tune a rolling update: maxSurge and maxUnavailable

**CKAD** lab, *Application Deployment* domain (20 % of the exam),
competency "Understand Deployments and how to perform rolling updates".

The inherited lab asked for an "evidence" ConfigMap copying the values
back: it proved nothing. Here the proof is in the ReplicaSets, the old one
at zero, the new one complete.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Rolling Updates and Rollbacks](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rolling-updates-rollbacks/) |

```bash
dsoxlab run   ckad-rolling-update-strategy
dsoxlab check ckad-rolling-update-strategy
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
