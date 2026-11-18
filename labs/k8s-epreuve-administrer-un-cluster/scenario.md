# Level 4 test: administer a cluster

## The situation

You take over, at short notice, the kubeadm cluster that hosts the **shop**.
The previous team leaves you an inherited state, and a list of problems:

- the control plane **`k8s-cp.lab`** is a mess: the node is NotReady and
  `kubectl` no longer answers;
- the worker **`k8s-w1.lab`** has been reset and is no longer in the cluster;
- last night, a wrong move **deleted the whole shop**. An etcd backup from the
  day before exists: **`/var/backups/etcd/etcd-veille.db`**. Since then,
  someone wrote an object named **`apres-la-veille`** into the cluster, which
  has no business there;
- the shop's manifests live in the git repository **`~/epreuve/manifestes`**,
  and some of them date from a bygone era;
- the cluster runs **1.36.4** and must move to **1.37.0**;
- two certificates of the control plane were reissued for a few days only;
- once the shop is back, its **`panier`** component does not start.

Management also wants proof that a **highly available** control plane survives
the loss of one of its members. With no three spare machines, it hands you the
host **`k8s-kind.lab`**, where Docker and kind are installed. You build there a
kind cluster named **`ha`**, with the catalogue's node image:

```text
kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

You are on `k8s-cp.lab`, with `kubectl` configured and `sudo` rights.
`ssh k8s-w1.lab` and `ssh k8s-kind.lab` open a session on the two other
machines, where you also have `sudo`. `etcdctl` and `etcdutl` are installed on
the control plane, at the version of its etcd.

## The requirements

1. The worker **`k8s-w1.lab`** is part of the cluster again, **Ready**, and its
   kubelet reports a **1.37** version.
2. **Swap** is off on the worker, and **nothing will turn it back on** at the
   next boot.
3. Cluster **`ha`** has **three control planes**, all **Ready**, read through
   the **address of the load balancer** placed in front of their API servers.
4. The **API** of `ha` still answers **through that address** when one of its
   control planes is down.
5. **Before restoring anything**, a fresh etcd backup is taken in
   **`/var/backups/etcd/etcd-avant-restauration.db`**, and checked.
6. The shop is back **through a restore** of the previous day's backup: these
   are **the same objects**, not copies recreated from the repository.
7. The **`apres-la-veille`** object no longer exists, and **every node** is
   **Ready**.
8. At the **last commit** of the repository, no manifest uses an API removed
   from Kubernetes any more, and the API server **accepts all of them**. None
   disappears from the repository: they are migrated.
9. The API server and **every node** report **1.37.0**, no node was left out
   of scheduling, and the storefront keeps **all its replicas ready**.
10. During any voluntary maintenance, the storefront keeps **at least one
    replica available**, and the cluster guarantees it.
11. The worker was **emptied** without cutting the shop, then **brought back
    into service**: it accepts Pods again.
12. The NotReady node is **Ready**, and its kubelet **will start on its own**
    after a reboot.
13. The API server answers again and **still authorizes** requests through the
    **Node** and **RBAC** modes.
14. **`panier`** has all its replicas available, **no longer restarts**, and
    reads its configuration where it looks for it.
15. **Before each repair**, the cause is recorded, from `describe`, the events
    or the logs, in **`~/epreuve/constats/`**: a **`kubelet.txt`** file, an
    **`apiserver.txt`** file and a **`panier.txt`** file, each naming what was
    at fault. Afterwards, leave them untouched: their date is compared with the
    start of what was repaired.
16. What you changed **live** on `panier` carries **the same value** at the
    last commit of the repository, with no difference from the cluster.
17. **No certificate** of the control plane expires in less than **thirty
    days**.
18. The storefront's replicas run on **different nodes**, and none receives
    traffic **before it is ready to serve**.

## How you are graded

The test is graded on the **final state** of both clusters, the repository and
the records, never on the commands typed. It has **eighteen criteria** of equal
weight. The threshold is **70 out of 100**, and **seven criteria are
critical**: they must all pass, whatever the total. They are criteria **1, 3,
4, 6, 9, 12 and 13**.

The order you work in matters: a restore brings the whole cluster back to the
day before, including whatever you did to it before the restore.

Every check acts on the clusters: the grader **stops a control plane of `ha`
itself** (it freezes its container) then starts it again, and launches a
short-lived Pod in the shop, `sonde-placement`, that the scheduler must place
on the worker. The feedback is limited to the list of unmet criteria, by their label, and the score: no message says why.

There is no hint: the test is passed without help, the way it is graded.

```bash
dsoxlab check  k8s-epreuve-administrer-un-cluster
dsoxlab submit k8s-epreuve-administrer-un-cluster
```
