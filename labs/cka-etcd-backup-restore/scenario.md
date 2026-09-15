# Back up etcd, then restore the cluster from a snapshot

## The situation

This morning, the namespace **`important-data`** is gone. It held a ConfigMap
**`mission-critical`** that the team needs today, and nobody knows what
happened.

An etcd backup was taken yesterday evening, before the incident:
**`/opt/backup/etcd-snapshot-previous.db`**. The cluster is a kubeadm cluster
with a single control plane, **`k8s-cp.lab`**, where you are connected with
`sudo` rights. The tools `etcdctl` and `etcdutl` are installed, in the version
of the etcd that is running.

## What you must achieve

1. **Before anything else**, a fresh backup of the current state in
   **`/opt/backup/etcd-snapshot.db`**, verified. You never restore without
   having backed up what you are about to overwrite.

2. The cluster **restored from yesterday evening's backup**, into a fresh data
   directory, with etcd running on it. The namespace `important-data` and its
   ConfigMap are back, just as they were.

3. A **healthy** cluster after the operation: the API answers, both nodes are
   `Ready`, and whatever the API server held in cache before the restore is no
   longer hanging around.

## Useful bearings

On this cluster, etcd is a static Pod: its manifest in
`/etc/kubernetes/manifests` says where its certificates are, where its data
directory is, and under what name it knows itself. The kubelet restarts that
Pod as soon as the manifest changes, and stops it as soon as the manifest
leaves the directory. Stopping the kubelet, on the other hand, stops no
container.

Since etcd 3.6, `etcdctl` only knows how to take a snapshot; verifying it and
restoring it are the work of `etcdutl`, offline, into a directory that does not
exist yet. The member name, the initial cluster and the peer URL you give it
must be those of the manifest.

The API server keeps in memory what it read from etcd. Restoring under its feet
without restarting it leaves that cache out of step with the database.

## How you will know it works

The tests read the fresh snapshot, the date of the data directory that the
running etcd uses, the UIDs of the objects that came back, and look for an
object created after yesterday evening's backup, which must no longer exist.

```bash
dsoxlab check cka-etcd-backup-restore
```
