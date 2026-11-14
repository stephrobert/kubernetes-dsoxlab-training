# Challenge: back up, restore and put a cluster back in order

Challenge of the module Administer the cluster of level 4, with no procedure: a
fresh etcd backup, a restore from the previous day's backup, a manifest
repository to migrate off removed APIs, certificates to renew. Graded on the
state of the cluster; the cleanup brings etcd back to `/var/lib/etcd`.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster |
| Duration | about 50 minutes |
| Companion lesson | [Cluster PKI, Practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-challenge-sauvegarder-et-restaurer
dsoxlab check k8s-challenge-sauvegarder-et-restaurer
```
