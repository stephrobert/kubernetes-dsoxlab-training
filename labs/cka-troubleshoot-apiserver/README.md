# Bring the API server back into service

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competency
"Troubleshoot cluster components".

This lab exists because the course **cannot prove it on kind**: the static
manifest, the kubelet that rereads it and the runtime that keeps the logs of
the dead container are those of a real machine. With no API, you have to
know how to do without `kubectl`.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Kubernetes control plane](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/control-plan/) |

```bash
dsoxlab run   cka-troubleshoot-apiserver
dsoxlab check cka-troubleshoot-apiserver
```

Ported from K8sExamLab on 2026-09-14, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
