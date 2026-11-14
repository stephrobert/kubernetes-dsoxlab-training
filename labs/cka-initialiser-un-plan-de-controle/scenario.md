# Initialise a control plane with kubeadm

## The situation

The cluster has been taken down: **`k8s-cp.lab`** and **`k8s-w1.lab`** were
reset with `kubeadm reset`. On `k8s-cp.lab`, the node preparation was undone
too. The team wants a new control plane, built properly: from a
**configuration file** it can read again and keep under version control, on a
machine that stays ready **after a reboot**.

You are on **`k8s-cp.lab`**, with `sudo` rights. The Calico v3.32.2 manifests
wait for you in **`~/kubeadm/calico/`**: no Internet needed for the network.
The worker is not to be joined in this lab.

## What you must achieve

1. The cluster is initialised from the file **`~/kubeadm/init.yaml`**. It is
   named **`catalogue`**, and its pod network is **`10.244.0.0/16`**.
2. Your **kubeconfig** (`~/.kube/config`) reaches this new cluster **without
   `sudo`**.
3. **Calico** runs on `k8s-cp.lab`.
4. The node is **Ready**, and **CoreDNS** runs.
5. The node preparation **survives a reboot**: `overlay` and `br_netfilter`
   modules, `net.ipv4.ip_forward = 1`, swap off.
6. **kubeadm**, **kubelet** and **kubectl** are **held**.

## Useful pointers

- `kubeadm init` checks the machine **before** changing anything (the
  *preflight*). Its errors tell what is missing.
- A setting made at runtime (`modprobe`, `sysctl -w`, `swapoff`) is gone after
  a reboot. What makes it last lives in `/etc/modules-load.d/`,
  `/etc/sysctl.d/` and `/etc/fstab`.
- The kubeadm configuration file holds `InitConfiguration` and
  `ClusterConfiguration` documents (API `kubeadm.k8s.io/v1beta4`).
  `kubeadm config print init-defaults` shows a full example.
- `kubeadm version -o short` gives the installed version. Without a version
  written in the file, kubeadm asks the Internet for one.
- The cidr in `~/kubeadm/calico/installation.yaml` must be the cluster's pod
  network.
- The configuration kubeadm actually used can be read back in the
  `kubeadm-config` ConfigMap of the `kube-system` namespace.
