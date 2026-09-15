# Install, upgrade and roll back with Helm 4

**CKAD** lab, *Application Deployment* domain (20 % of the exam), competency
"Use the Helm package manager to deploy existing packages".

Helm 4.3.0, the current version. The inherited lab went through the Bitnami
charts, whose images are no longer served freely: the chart is local, generated
by `helm create`, with an image aligned on the rest of the catalogue.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Installing and managing Helm releases](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/helm/install-releases/) |

```bash
dsoxlab run   ckad-helm-install-upgrade
dsoxlab check ckad-helm-install-upgrade
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
