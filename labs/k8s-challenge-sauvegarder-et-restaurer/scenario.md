# Challenge: back up, restore and put a cluster back in order

## The situation

Last night, someone deleted the **`facturation`** namespace and its
**`tarifs`** ConfigMap. Since then, an object has been written to the cluster:
**`intrus-apres-sauvegarde`**, in `default`. The previous day's backup is in
**`/var/backups/etcd/etcd-veille.db`**.

The same audit lists two more debts: the manifest repository **`~/depot`** no
longer applies, and a control plane certificate is nearing expiry.

You are on **`k8s-cp.lab`**, the control plane, with `kubectl`, `etcdctl`,
`etcdutl` and `sudo` rights. No procedure is given.

## What you must achieve

1. A **fresh backup** of etcd in **`/var/backups/etcd/etcd-fraiche.db`**, taken
   **before** any restore.
2. **etcd** runs on a **new data directory**, restored from the previous day's
   backup, and the cluster is **healthy**: API and both nodes Ready.
3. **`facturation`** and **`tarifs`** are back **unchanged**.
4. **`intrus-apres-sauvegarde`** no longer exists.
5. The manifests of **`~/depot`** use **current APIs** and their objects exist in
   the **`depot`** namespace, with their settings.
6. **No control plane certificate** expires within **thirty days**.

## Grading

Each state counts equally; the pass mark is 70 %. Only the verdict is shown.
