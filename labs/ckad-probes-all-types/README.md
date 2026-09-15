# Three probes on one Pod: startup, liveness, readiness

**CKAD** lab, *Application Observability and Maintenance* domain (15 % of the
exam), competency "Implement probes and health checks".

The inherited lab only checked that the probes were present. Here the Pod
must be `Ready` with no restart: that is the proof that the probes find what
they are looking for, and a probe aimed at a wrong path would not pass.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Defining Probes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/probes/) |

```bash
dsoxlab run   ckad-probes-all-types
dsoxlab check ckad-probes-all-types
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
