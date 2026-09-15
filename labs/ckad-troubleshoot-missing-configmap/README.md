# A Pod blocked by a ConfigMap that does not exist

**CKAD** lab, *Application Observability and Maintenance* domain (15 % of
the exam), competency "Debugging in Kubernetes".

The failure with no logs: the container does not exist yet, and only the
events talk. The inherited lab checked that the ConfigMap exists; here the
application must serve what it contains.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Debugging an application](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/) |

```bash
dsoxlab run   ckad-troubleshoot-missing-configmap
dsoxlab check ckad-troubleshoot-missing-configmap
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
