# Challenge: Harden a worker node and the access to the API server, without breaking the cluster

## 📍 The situation

The second worker **`k8s-w2.lab`** has just joined the cluster. It was
installed from an old server template, which left on it many things
Kubernetes does not need. A contractor ("prestataire") also had access to it,
and the contract is over.

On the control plane side, the API server still answers clients with no
credentials, and someone gave those clients the right to read the cluster.

You are on the control plane, with `kubectl` and `sudo`. You open a session on
the node with `ssh k8s-w2.lab`. No procedure is given: the module taught you
what you need.

What must keep working during and after your work:

- **SSH (22)** to `k8s-w2.lab`, from the **administration workstation** (the
  address your sessions on the control plane come from) and from the
  **control plane**;
- the **kubelet (10250)** of the node, from the cluster nodes and from the Pod
  network;
- the **Calico** network plugin between the nodes: **BGP (TCP 179)** and
  **VXLAN (UDP 4789)**;
- the **health probes** of the API server and **joining a new node** with
  `kubeadm join`.

## 🎯 What you must achieve

1. `k8s-w2.lab` no longer runs what it does not need: the **apache2** web
   server is **purged**, and the **inventory report** ("relevé d'inventaire")
   listening on port **9090** is stopped and disabled.

2. Only the members of the **`ops-noeuds`** group open an SSH session on
   `k8s-w2.lab`. This group holds `ansible` and `student`. sshd accepts
   **keys** only, and **root** does not log in.

3. The **`prestataire`** account stays on the node, its files kept for the
   audit, but it has **no sudo rights left**.

4. The **kubelet** of `k8s-w2.lab` answers **401** to an anonymous client,
   **delegates** its authorization decisions to the API server, and its
   **read-only port** 10255 is closed.

5. An nftables input chain with policy **`drop`** closes `k8s-w2.lab`. A node
   that is not an administration workstation, such as `k8s-w1.lab`, no longer
   reaches SSH or port 10256. The flows listed above still pass.

6. An anonymous client only reaches the health paths (`/livez`, `/readyz`,
   `/healthz`) and what `kubeadm join` needs. Everywhere else, the API server
   answers **401**. The authentication configuration lives in
   **`/etc/kubernetes/authn-config.yaml`**. No RBAC binding grants rights to
   anonymous clients besides those the API server and kubeadm create
   themselves. **Blocking requirement.**

7. All of the above **survives a reboot** of `k8s-w2.lab`, and the node comes
   back **Ready**. **Blocking requirement.**

## ✅ How you will know it works

The tests read the ports actually listening, open real SSH sessions, ask sudo
for the rights of the contractor, query the kubelet and the API server with no
credentials then with an account that has no rights, and open fresh
connections from `k8s-w1.lab` and from the control plane. They also place a
Pod on `k8s-w2.lab` and reach it through a Service from `k8s-w1.lab`. The last
test **reboots `k8s-w2.lab`** and runs its checks again.

Seven requirements, equal weight. The pass mark is 70%, and both blocking
requirements must hold. The feedback is limited to the list of unmet criteria
and the score.

```bash
dsoxlab check k8s-challenge-durcir-les-noeuds-et-l-acces-api
```
