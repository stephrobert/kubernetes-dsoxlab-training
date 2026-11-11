# Create a multi-node kind cluster

Guided lab of the **Fondamentaux** module of the Kubernetes course: describe a
cluster of one control plane and two workers in a kind configuration file, then
create it on the pinned node image.

| | |
|---|---|
| Target | `k8s-kind.lab`, Docker and kind; the lab deletes the clusters of the other labs, which their own setup recreates |
| Duration | about 15 minutes |
| Related page | [Créer votre premier cluster, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/fondamentaux/premier-cluster/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-creer-un-cluster-kind
dsoxlab check k8s-creer-un-cluster-kind
```
