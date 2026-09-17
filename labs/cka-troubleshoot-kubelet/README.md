# Repair a kubelet that refuses to start

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competencies
"Troubleshoot clusters and nodes" and "Troubleshoot cluster components".

This lab exists because the training **cannot prove it on kind**: a kubelet is
a systemd service, its journal is that of a real machine, and its configuration
is the one `kubeadm` wrote. Wave 1 of the backlog asked for it under the name
`cka-reparer-un-kubelet`.

| | |
|---|---|
| Targets | `k8s-cp.lab`, and `k8s-w1.lab` reachable over `ssh` from the control plane |
| Duration | about 15 minutes |
| Companion lesson | [Worker nodes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/worker-nodes/) |

```bash
dsoxlab run   cka-troubleshoot-kubelet
dsoxlab check cka-troubleshoot-kubelet
```

Ported from K8sExamLab on 2026-09-14, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
