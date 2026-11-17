# Close a worker node to the network, except the flows Kubernetes needs

## The situation

The second worker **`k8s-w2.lab`** has **no firewall**: every listening port
answers the whole network. You open a session on it from the control plane
with `ssh k8s-w2.lab`, as an account that has `sudo`.

What must keep flowing:

- **SSH (22)**, from the **administration workstation** (the address your
  sessions on the control plane come from) and from the **control plane**
  itself;
- the **kubelet (10250)**, from the cluster **nodes** and from the **Pod
  network** (`metrics-server` reads it from a Pod);
- the **Calico** network plugin from the nodes: **BGP (TCP 179)** and the
  **VXLAN** tunnel **(UDP 4789)**.

Everything else closes, including the kube-proxy health port (10256).

## What you must achieve

1. An nftables input chain with a **`drop` policy** is loaded on
   `k8s-w2.lab`. A node that is not an administration host, such as
   `k8s-w1.lab`, reaches neither SSH nor port 10256 anymore.
2. The cluster flows pass: the nodes reach the kubelet, the control plane
   reaches SSH, `kubectl logs` works on a Pod of `k8s-w2.lab`, and a Pod of
   `k8s-w1.lab` reaches a Pod of `k8s-w2.lab` through a Service.
3. The rules **survive a reboot** of `k8s-w2.lab`, without erasing those of
   kube-proxy and Calico.

## Landmarks

Read the values before writing: `kubectl get nodes -o wide` for the node
addresses, the `podSubnet` of the `kubeadm-config` ConfigMap (namespace
`kube-system`) for the Pod network, `echo $SSH_CONNECTION` on the control plane
for the workstation address.

kube-proxy and Calico write their own rules into the kernel. A table of your
own, without **`flush ruleset`**, lives alongside them. Before loading a `drop`
policy, schedule its automatic removal with `systemd-run`: if you cut your own
session, it will fall by itself a few minutes later.

The Ubuntu `nftables` service reloads `/etc/nftables.conf` at boot. The shipped
file starts with `flush ruleset`. And stopping it (`systemctl stop`, so also
`restart` on an active service) empties the **whole** ruleset: on a Kubernetes
node, reload with `nft -f` or `systemctl reload nftables`.

An already open connection passes a `ct state established` rule: always test
with a **new** connection.

## How you will know it works

The tests read the loaded ruleset, open new connections from `k8s-w1.lab` and
the control plane, make two Pods talk across the node, then **reboot**
`k8s-w2.lab` and check that the firewall came back.

```bash
dsoxlab check cks-fermer-l-acces-reseau-au-noeud
```

If you locked yourself out and the safety net did not fire:
`dsoxlab destroy --optional-hosts`, then
`dsoxlab run cks-fermer-l-acces-reseau-au-noeud`.
