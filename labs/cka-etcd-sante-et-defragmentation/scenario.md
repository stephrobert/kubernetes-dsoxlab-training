# Check etcd health and defragment its database

## The situation

etcd holds the whole state of the cluster. An unhealthy etcd, or a database
nearing its quota, and the API server stops writing. A team created then deleted
many objects: the database grew, and it did not shrink back.

You are on **`k8s-cp.lab`**, the control plane of the kubeadm cluster, with
`kubectl` configured. etcd runs there as a static Pod, **`etcd-k8s-cp.lab`**,
and its image contains `etcdctl`. Its certificates are under
`/etc/kubernetes/pki/etcd/`.

## What you must achieve

1. In **`~/etcd/reponses.yaml`**: the etcd **member ID** (in hexadecimal), its
   **client endpoint**, and whether it is **healthy**.
2. In the same file: the **space quota** this etcd applies, in bytes.
3. The etcd database is **defragmented**: it gave back the space the deleted
   objects still took.

## Useful bearings

- `etcdctl` requires the TLS certificates: `--cacert`, `--cert`, `--key`. The
  static Pod's options, in `/etc/kubernetes/manifests/etcd.yaml`, tell which
  ones to use.
- `etcdctl member list`, `endpoint health` and `endpoint status` answer the
  first two questions. `-w table` or `-w json` change the output.
- An etcd without a `--quota-backend-bytes` option applies the default value,
  which the lesson gives.
- **Compaction** removes old revisions and frees space **inside** the file. Only
  **defragmentation** gives that space back to the disk. `endpoint status` shows
  the database size before and after.

## How you will know it works

The tests query etcd with its certificates and compare your answers with what it
says of itself, then measure the database size against the one the setup
recorded.

```bash
dsoxlab check cka-etcd-sante-et-defragmentation
```
