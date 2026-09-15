# Restore traffic to a Service

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competency
"Troubleshoot services and networking".

Three failures stacked on top of each other, as in the exam: a selector that
finds nothing, a port that leads nowhere, and a network policy that closes
everything. The last test makes a real request, which requires a CNI that
enforces NetworkPolicy: it is for this lab, among others, that the shared base
moved to Calico.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Services](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |

```bash
dsoxlab run   cka-troubleshoot-networking
dsoxlab check cka-troubleshoot-networking
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
