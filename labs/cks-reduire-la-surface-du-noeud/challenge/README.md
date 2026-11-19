# Challenge: Remove from a worker node what listens without serving Kubernetes

## The situation

The second worker **`k8s-w2.lab`** was installed from an old server template.
You open a session on it from the control plane with `ssh k8s-w2.lab`, as an
account that has `sudo`.

A scan from the network found, on top of what a worker uses, **three open
ports** on this node. None of them serves Kubernetes. Every listening service
is one more door for an attacker, and every installed package is code to patch
at each published flaw.

What a cluster worker really uses, on all its interfaces: `sshd` (22), `bird`,
the BGP of Calico (179), the kubelet (10250), kube-proxy (10256), the VXLAN
tunnel of Calico (UDP 4789), and the DHCP client (UDP 68, bound to the node
address). Add `calico-typha` (5473) when the Calico operator places an
instance on this node.

## What you must achieve

1. Nothing listens on the interfaces of `k8s-w2.lab` beyond the list above.
   Ports **111**, **21** and **8000** refuse a connection coming from the
   control plane.
2. The removal **lasts**: the useless packages are **purged**, and what no
   package ships is stopped and **disabled**. Nothing may come back at the next
   boot.
3. The node stays a Kubernetes node: the kubelet, containerd and sshd run, the
   node is `Ready`, and a Pod placed on it starts.

## Landmarks

`sudo ss -tulpn` lists what listens and names the process. An address
`127.0.0.1` or `::1` can only be reached from the machine itself: it is not
part of the exposed surface.

Go back from each process to its systemd unit, then to its package. A service
can be restarted by a systemd **socket**: stopping the service then does not
close the port. A service no package ships will not leave with `apt`.

Keep the removal for the end, once every port is tied to its source: a package
removed by mistake, containerd or the kubelet, takes the node out of the
cluster.

## How you will know it works

The tests read what listens on `k8s-w2.lab`, try each port from the control
plane, read the state of the packages and units, then place a Pod on the node.

```bash
dsoxlab check cks-reduire-la-surface-du-noeud
```
