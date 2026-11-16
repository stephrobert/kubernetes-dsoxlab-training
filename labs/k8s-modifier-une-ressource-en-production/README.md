# Change a live Deployment without losing a container, and resolve the drift

**CKA** lab, *Workloads and Scheduling* domain, competency "Understand
application deployments and how to perform rolling updates and rollbacks".

`edit`, `patch` and `replace` write straight into the cluster. Each has its
trap: JSON merge wipes out a container, `replace --force` stops everything, and
any fix made outside Git will be undone at the next `apply`. This lab puts them
into play on a two-container Deployment that is already drifting.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | about 25 minutes |
| Lesson | [Modifier une ressource en production : edit, patch, replace](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-edit-patch-replace/) (French) |

```bash
dsoxlab run   k8s-modifier-une-ressource-en-production
dsoxlab check k8s-modifier-une-ressource-en-production
```
