# Back up etcd, then restore the cluster from a snapshot

**CKA** lab, *Cluster Architecture, Installation and Configuration* domain
(25 % of the exam), competency "Perform etcd backup and restore".

This lab exists because the training **cannot prove it on kind**: restoring
etcd there costs you the cluster. Wave 1 of the backlog asked for it under the
name `cka-restaurer-etcd`, with this note: "the restore has not been played
through". It is played here, and playing it showed that the procedure as taught
stopped the kubelet, which does not stop etcd. The lesson has been fixed.

The inherited lab had the candidate delete the namespace and checked the
snapshot with `etcdctl snapshot status`, a command that no longer exists in
etcd 3.7 and yet returns 0. Here the loss has already happened, a backup from
the previous evening exists, and the tests prove the restore through the date
of the data directory in service, the UIDs of the objects that came back, and
the disappearance of an object written after the backup. The identity of the
etcd member is of no use for that: measured identical before and after the
restore, since etcd computes it from the peer URLs and the cluster token.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [etcd, the key/value store of the control plane](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/) |

```bash
dsoxlab run   cka-etcd-backup-restore
dsoxlab check cka-etcd-backup-restore
```

The cleanup brings etcd back onto `/var/lib/etcd` with the original manifest,
keeping the current data, and falls back on a safety snapshot if the candidate
broke the cluster.

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
