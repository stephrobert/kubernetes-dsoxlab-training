# Get a Pod out of ImagePullBackOff

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competencies
"Troubleshoot clusters and nodes" and "Manage and evaluate container output
streams".

An image that will not download is the first failure every beginner runs into,
and the exam poses it in five minutes. The message that solves it is in the
events, not in the status.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Diagnosing an ImagePullBackOff](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/) |

```bash
dsoxlab run   cka-troubleshoot-imagepullbackoff
dsoxlab check cka-troubleshoot-imagepullbackoff
```

Ported from K8sExamLab on 2026-09-14, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
