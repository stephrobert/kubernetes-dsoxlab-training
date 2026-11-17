# Install Cilium without kube-proxy

## The situation

The network team wants a cluster whose Services are no longer served by
kube-proxy and its thousands of iptables rules, but by Cilium and eBPF. You
have three machines for it: **`net-cp.lab`**, the control plane, and two
workers, **`net-w1.lab`** and **`net-w2.lab`**.

The three nodes are ready: swap off, containerd configured, `kubelet`,
`kubeadm` and `kubectl` 1.37 installed and held, `helm` 4.3.2 on the control
plane. No cluster exists yet. From the control plane, `ssh net-w1.lab` and
`ssh net-w2.lab` open a session on each worker without a password, and `sudo`
needs none either.

The node network is `10.10.50.0/24`. The default Pod pool of Cilium,
`10.0.0.0/8`, contains it: a Pod could receive an address that hides a node.
The team has chosen the pool **`10.244.0.0/16`**, one `/24` block per node.

Version note: Cilium 1.20.4 declares support for Kubernetes 1.33 to 1.36, and
this cluster runs 1.37. The lab runs on this combination, which sits outside
what Cilium officially declares: an unexpected behaviour may come from there.

## What you must obtain

1. A cluster initialised on `net-cp.lab` **without kube-proxy**: neither its
   DaemonSet nor its ConfigMap in `kube-system`.
2. Both workers **joined**, and the three nodes **Ready**.
3. **Cilium 1.20.4** installed with Helm on every node, with the agent
   reporting **`KubeProxyReplacement: True`**.
4. **No kube-proxy rule** on any node: no `KUBE-SVC` or `KUBE-SERVICES` chain.
5. A Deployment **`web`** (image `nginx:1.30.6`, 2 replicas) in the namespace
   **`demo`**, exposed by a ClusterIP Service **`web`** on port 80, which
   answers from a worker and appears in Cilium's service table.
6. IPAM in **`cluster-pool`** mode on the pool **`10.244.0.0/16`**, `/24` per
   node.

## The method, step by step

**Initialise without kube-proxy.** kubeadm installs kube-proxy as an addon
phase, which can be skipped: `sudo kubeadm init
--skip-phases=addon/kube-proxy`. Then give yourself a kubeconfig, as the
command's output says (`$HOME/.kube/config`). `kubectl -n kube-system get ds`
shows no kube-proxy.

**Join the workers.** `sudo kubeadm token create --print-join-command` gives
the command to run with `sudo` on each worker, through `ssh net-w1.lab` then
`ssh net-w2.lab`. The nodes appear `NotReady`: there is no CNI yet, which is
expected.

**Install Cilium as the kube-proxy replacement.** Declare the chart repository
(`helm repo add cilium https://helm.cilium.io`), then install the chart
`cilium/cilium` **version 1.20.4** in `kube-system`. The values that matter:

- `kubeProxyReplacement=true`;
- `k8sServiceHost` and `k8sServicePort`: the address of the control plane
  (`ip -4 route get 1.1.1.1` gives it after `src`) and `6443`. Without
  kube-proxy, nothing serves the `kubernetes` Service to an agent that starts:
  it must reach the API server directly;
- `ipam.mode=cluster-pool`, `ipam.operator.clusterPoolIPv4PodCIDRList` set to
  `{10.244.0.0/16}` and `ipam.operator.clusterPoolIPv4MaskSize=24`. The pool is
  fixed at install time: changing it afterwards does not move the blocks
  already allocated.

`kubectl -n kube-system rollout status ds/cilium`, then `kubectl get nodes`:
the three nodes turn `Ready`.

**Read what Cilium says.** `kubectl -n kube-system exec ds/cilium -c
cilium-agent -- cilium-dbg status` prints a `KubeProxyReplacement:` line. On
each worker, `sudo iptables-save -t nat | grep KUBE-SVC` returns nothing.

**Serve a Service.** Create the namespace `demo`, the Deployment `web` and its
Service. From a worker, `curl http://<ClusterIP>/` answers, and `cilium-dbg
service list` in an agent shows the ClusterIP with its two backends. The
packet never went through iptables.

**Read the IPAM.** `kubectl get ciliumnodes -o wide` shows the block of each
node, and `kubectl -n demo get pods -o wide` the Pod addresses, inside
`10.244.0.0/16`.

## How you will know it works

The tests ask the API server for kube-proxy, the nodes and the CiliumNodes,
run `cilium-dbg status` in every agent, read the nat table of the three nodes,
then call the `web` Service from `net-w1.lab`.

```bash
dsoxlab check k8s-installer-cilium-sans-kube-proxy
```
