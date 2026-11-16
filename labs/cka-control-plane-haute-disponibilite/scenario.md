# Build a kubeadm control plane with three nodes behind a load balancer, and lose one

## The situation

The team wants a cluster that survives the loss of a control-plane machine.
Four machines have been prepared for you:

- **`ha-cp1`**, **`ha-cp2`** and **`ha-cp3`**: ready for kubeadm (swap off,
  containerd, kubelet, kubeadm and kubectl 1.37), **without any cluster**;
- **`ha-lb`**: an **HAProxy** load balancer that listens on
  **`ha-lb.lab:6443`** and forwards to port 6443 of the three nodes.

You are on `ha-cp1`. From there, `ssh ha-cp2` and `ssh ha-cp3` open a session
without a password, and `sudo` is available everywhere.

## What you must achieve

1. The cluster's access point is the **load balancer**, `ha-lb.lab:6443`.
2. **`ha-cp1`, `ha-cp2` and `ha-cp3`** are all three `Ready` **control
   planes**, in 1.37.
3. **etcd has three voting members**, all healthy (stacked etcd, one member
   per control plane).
4. The cluster **survives the loss of a control plane**: with `ha-cp2` down,
   you can still write into the cluster through the load balancer.

## Landmarks

The access point is set at initialisation (`--control-plane-endpoint`) and
**cannot be changed afterwards**. `--upload-certs` stores the cluster
certificates in a Secret, where the other control planes fetch them with their
certificate key (valid two hours).

A node joined without `--control-plane` becomes a worker. A node stays
`NotReady` as long as no CNI is installed: the lesson uses Flannel, with the
Pod network `10.244.0.0/16`.

`etcdctl` is not installed on a kubeadm node: it runs inside the etcd Pod,
with the certificates of `/etc/kubernetes/pki/etcd/`.

If the initialisation goes wrong, `sudo kubeadm reset -f` resets a node.

## How you will know it works

The tests read the kubeadm configuration, the nodes and the etcd members.
Then they stop `ha-cp2` (its kubelet and its containers), write into the
cluster through the load balancer, restart `ha-cp2` and wait for its etcd
member to come back.

```bash
dsoxlab check cka-control-plane-haute-disponibilite
```
