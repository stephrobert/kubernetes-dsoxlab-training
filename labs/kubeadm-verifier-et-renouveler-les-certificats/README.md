# Check and renew the certificates of a kubeadm cluster

First guided lab of the "Kubernetes cluster PKI" lesson, Administer the cluster
module of level 4: read the expiry dates, renew the control plane certificates,
make the components reload them, copy admin.conf again. Renewal is judged on
serial numbers, recorded when the lab starts.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster |
| Duration | about 30 minutes |
| Related page | [Cluster PKI, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/#mettre-en-pratique) |

```bash
dsoxlab run   kubeadm-verifier-et-renouveler-les-certificats
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```
