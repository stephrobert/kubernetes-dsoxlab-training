# Detect and migrate removed APIs before an upgrade

Challenge of the Kubernetes training, in the Put it into practice section of
the "Manage API deprecations" lesson: find the manifests of a repository that
use a removed API, name them with their replacement in a report, migrate them
without changing their intent, and apply the repository. Five requirements,
pass mark 80%, two of them blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the lab sets up the `plateforme` namespace and the `~/plateforme` repository |
| Duration | about 40 minutes |
| Related page | [Manage API deprecations, Put it into practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/manage-api-deprecations/#put-it-into-practice) |

```bash
dsoxlab run    k8s-challenge-migrer-les-api-retirees
dsoxlab check  k8s-challenge-migrer-les-api-retirees
dsoxlab submit k8s-challenge-migrer-les-api-retirees
```
