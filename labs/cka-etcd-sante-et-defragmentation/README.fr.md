# Contrôler la santé d'etcd et défragmenter sa base

Lab guidé de la leçon « etcd », module Administrer le cluster du niveau 4 : lire
la santé d'etcd, son membre et son quota avec etcdctl et ses certificats, puis
défragmenter une base que le setup a gonflée. La sauvegarde et la restauration
restent au lab `cka-etcd-backup-restore`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue |
| Durée | environ 25 minutes |
| Page associée | [etcd, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/#mettre-en-pratique) |

```bash
dsoxlab run   cka-etcd-sante-et-defragmentation
dsoxlab check cka-etcd-sante-et-defragmentation
```
