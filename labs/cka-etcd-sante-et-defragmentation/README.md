# Check etcd health and defragment its database

Guided lab of the "etcd" lesson, Administer the cluster module of level 4: read
etcd health, its member and its quota with etcdctl and its certificates, then
defragment a database the setup bloated. Backup and restore stay with the
`cka-etcd-backup-restore` lab.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster |
| Duration | about 25 minutes |
| Related page | [etcd, Put into practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/etcd/) |

```bash
dsoxlab run   cka-etcd-sante-et-defragmentation
dsoxlab check cka-etcd-sante-et-defragmentation
```
