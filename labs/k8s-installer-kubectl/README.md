# Install and configure kubectl

Guided lab of the **Fundamentals** module of the Kubernetes course: install the
official kubectl binary at a pinned version after checking its fingerprint,
turn on bash completion with the alias `k`, then check that it reaches a
cluster.

| | |
|---|---|
| Target | `k8s-kind.lab`; the lab prepares a kind cluster and your kubeconfig, then removes kubectl |
| Duration | about 20 minutes |
| Related page | [Install and configure kubectl, Mettre en pratique section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-installation-configuration/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-installer-kubectl
dsoxlab check k8s-installer-kubectl
```
