# Give a person access through a CertificateSigningRequest

Second guided lab of the "Kubernetes cluster PKI" lesson, Administer the cluster
module of level 4: camille's key and request, the approval, the certificate the
API issued, her kubeconfig, then read-only rights on one namespace, checked
under her identity. The CA key never leaves the node.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `equipe-web` namespace |
| Duration | about 25 minutes |
| Related page | [Cluster PKI, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-donner-un-acces-par-csr
dsoxlab check k8s-donner-un-acces-par-csr
```
