# Challenge: Attach a second network interface to a Pod with Multus

## The situation

The Cilium cluster of the `net-*` hosts has **three nodes**: `net-cp.lab`
(control plane), `net-w1.lab` and `net-w2.lab`. Cilium 1.20.5 replaces
kube-proxy and runs with its default setting **`cni.exclusive=true`**.

A storage team wants two Pods to talk over a **second network**, separate from
the cluster network: a macvlan network on the nodes' interface `enp1s0`, in
`192.168.100.0/24`. The manifest of **Multus v4.3.2** in thick mode is ready on
the control plane, its image pinned by digest:
`/opt/multus/multus-daemonset-thick.yml`. The namespace **`multus-demo`** is
empty. The CNI plugins `macvlan` and `static` are already on every node.

You are on `net-cp.lab`, with `kubectl` and `helm` configured.

## What you must achieve

1. Cilium **no longer owns** the CNI configuration alone: `cni-exclusive` is
   `false`, and every Cilium agent is ready.
2. **Multus v4.3.2** in thick mode runs on the three nodes, from the pinned
   image.
3. A NetworkAttachmentDefinition **`reseau-stockage`** in `multus-demo`
   describes a **macvlan** network on `enp1s0`, with **static** addresses.
4. Two Pods in `multus-demo` have **two interfaces** each: **`client`** on
   `net-w1.lab` with `192.168.100.11/24`, **`serveur`** on `net-w2.lab` with
   `192.168.100.12/24`. `serveur` answers HTTP on port **8080**.
5. From `client`, `http://192.168.100.12:8080/` answers, and the same server
   still answers on its cluster address.

## The method, step by step

**Let Cilium share the CNI configuration first.** In exclusive mode, the
Cilium agent renames any other file of `/etc/cni/net.d` to `.cilium_bak`,
Multus's included, without a word. `helm upgrade cilium cilium/cilium
--version 1.20.5 -n kube-system --reuse-values --set cni.exclusive=false`,
then wait for the agents (`kubectl -n kube-system rollout status ds/cilium`).
If Multus was installed before, its file stays renamed: the Multus Pod of the
node must be restarted to write it again.

**Install Multus.** `kubectl apply -f /opt/multus/multus-daemonset-thick.yml`
creates the DaemonSet `kube-multus-ds`, the CRD of the
NetworkAttachmentDefinitions and their roles. The upstream manifest of the
v4.3.2 tag points to the moving image `snapshot-thick`: this copy is pinned.
On each node, Multus writes `00-multus.conf`, first in alphabetical order, and
hands the cluster network to Cilium.

**Describe the second network.** A `NetworkAttachmentDefinition` carries a CNI
configuration in JSON under `spec.config`: `"type": "macvlan"`, `"master":
"enp1s0"`, `"mode": "bridge"`, and `"ipam": {"type": "static"}` so that each
Pod brings its own address.

**Attach it to the Pods.** The annotation `k8s.v1.cni.cncf.io/networks` names
the network and, with static addressing, the address:
`'[{"name": "reseau-stockage", "ips": ["192.168.100.11/24"]}]'`. Place each Pod
with `nodeName`. The image
`busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e`
can sleep for the client, and serve a page for the server with
`httpd -f -p 8080 -h /tmp`.

**Check.** `kubectl -n multus-demo exec client -- ip -4 addr` shows `eth0`
(Cilium) and `net1` (macvlan). The annotation
`k8s.v1.cni.cncf.io/network-status` of each Pod lists both networks. If a Pod
stays in `ContainerCreating`, `kubectl describe pod` gives the CNI error, word
for word.

## How you will know it works

The tests read the Cilium configuration, the Multus Pods and the image they
run, the NetworkAttachmentDefinition and the network status of both Pods.
Then they request the server from the client, through the second network and
through the cluster network.

```bash
dsoxlab check k8s-attacher-une-seconde-interface
```
