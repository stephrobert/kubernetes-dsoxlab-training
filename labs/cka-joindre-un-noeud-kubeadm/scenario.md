# Join a worker to a kubeadm cluster

## The situation

The worker **`k8s-w1.lab`** has been removed from the cluster and reset: it is
no longer a node, and its preparation has been undone. The team wants it back
in service, cleanly: a machine joined in a hurry falls over at its first
reboot.

You are on **`k8s-cp.lab`**, the control plane, with `kubectl` configured and
`sudo` rights. The worker is reached with `ssh k8s-w1.lab`, where you also have
`sudo`.

## What you must achieve

1. **`k8s-w1.lab`** is a node of the cluster, **Ready**.
2. Its **kubelet** reports the **same version** as the API server.
3. **Swap** is **off** on the worker, and **nothing will turn it back on** at
   the next boot.
4. **containerd** runs with the **systemd cgroup driver**, the kubelet's one.
5. **kubeadm**, **kubelet** and **kubectl** are **held** on the worker.
6. A **Pod** of the **`jonction`** namespace runs **on `k8s-w1.lab`**.

## Useful bearings

- The join is done **from the worker**, with a command **the control plane
  issues**: it carries a token with a limited lifetime and the hash of the
  cluster's CA.
- The kubelet **refuses to start** while swap is active. `swapon --show` says
  what is active, `/etc/fstab` what will be at boot.
- containerd's configuration lives in `/etc/containerd/config.toml`, and it
  only reads it **when it restarts**.
- `apt-mark` holds and unholds a package.
- A Pod is placed on a given node by the `nodeName` field of its spec, which
  bypasses the scheduler.
- A failing join reads in the output of `kubeadm join` and in the kubelet's
  journal: `journalctl -u kubelet`.
