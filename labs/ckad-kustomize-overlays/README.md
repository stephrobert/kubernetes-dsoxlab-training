# One Kustomize base and two overlays, dev and prod

**CKAD** lab, *Application Deployment* domain (20 % of the exam), competency
"Understand and use Kustomize".

The training has no Kustomize lesson yet: the companion lesson is the one on
Deployments, and the gap has been raised in the blog backlog.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Deployments](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/deployments/) |

```bash
dsoxlab run   ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
