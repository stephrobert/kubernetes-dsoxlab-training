# Bring a NotReady node back into the cluster

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competency
"Troubleshoot clusters and nodes".

This lab exists because the training **cannot prove it on kind**: the kubelet
is a systemd service on a real machine, and a second node is needed to break
one without breaking the API. It is the first lab in the catalogue to use the
`k8s-w1.lab` worker.

| | |
|---|---|
| Targets | `k8s-cp.lab`, and `k8s-w1.lab` reachable over `ssh` from the control plane |
| Duration | about 15 minutes |
| Companion lesson | [Diagnosing a cluster failure](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/) |

```bash
dsoxlab run   cka-troubleshoot-node-notready
dsoxlab check cka-troubleshoot-node-notready
```

Ported from K8sExamLab on 2026-09-14, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
