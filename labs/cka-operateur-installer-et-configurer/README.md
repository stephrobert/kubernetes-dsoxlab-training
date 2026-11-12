# Install an operator and configure what it runs

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain:
"Understand CRDs, install and configure operators". Guided lab of the
"Operators" lesson of the Kubernetes course.

The learner installs **MongoDB Controllers for Kubernetes 1.15.0** from its two
versioned manifests, images pinned by digest, hands it a one-member replica set,
then changes a mongod setting by editing only the resource.

The operator was chosen on its official compatibility matrix, which covers
Kubernetes 1.35, 1.36 and 1.37 (read on 2026-11-12). Licences: Apache 2.0 for
the operator driving MongoDB Community, SSPL v1 for the MongoDB server.

The setup installs `local-path-provisioner` v0.0.37 as the default class. The
`cleanup.yaml` removes the `mongodb` namespace, the operator's CRDs, cluster
permissions and webhook configuration, then the storage and its data on both
nodes.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 40 minutes, several of them pulling the server image (433 MB) |
| Companion lesson | [Operators](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators/#mettre-en-pratique) |

```bash
dsoxlab run   cka-operateur-installer-et-configurer
dsoxlab check cka-operateur-installer-et-configurer
```
