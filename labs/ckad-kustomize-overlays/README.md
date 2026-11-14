# One Kustomize base and two overlays, dev and prod

Lab of the **Kustomize** lesson of the "Deploy your applications" module of the
Kubernetes course, and **CKAD** skill of the *Application Deployment* domain:
one base, two overlays, a generated ConfigMap, an image change specific to one
environment, and a cluster that matches the folder.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 30 minutes |
| Related page | [Kustomize, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kustomize/) |

```bash
dsoxlab run   ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```
