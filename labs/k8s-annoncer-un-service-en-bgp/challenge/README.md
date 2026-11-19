# Challenge: Announce Pods and Services to a router with BGP

## The situation

The Cilium cluster of the `net-*` hosts has **three nodes**: `net-cp.lab`
(control plane), `net-w1.lab` and `net-w2.lab`. Cilium 1.20.5 replaces
kube-proxy, with the **BGP control plane turned off**.

Outside the cluster, a router of the network team runs **FRR 10.6.2**: AS
**65000**, address **10.10.50.200**. It already declares the three nodes as
neighbours, and expects them in AS **65001**. For now, its sessions stay in
`Active`: nobody answers.

In the namespace **`bgp-demo`**, the application `web` (nginx) is exposed by
the Service **`web`** of type `LoadBalancer`, labelled `annonce-bgp=oui`. The
cluster has no load balancer: its external address stays `<pending>`. The
network team gives you the block **`172.30.0.0/28`** for such addresses.

You are on `net-cp.lab`, with `kubectl` and `helm` configured. You cannot log
into the router: the tests will read it for you.

## What you must achieve

1. The Cilium **BGP control plane** is on, and every agent is ready.
2. The router has an **established session** with each of the three nodes.
3. The router has learnt the **Pod network** of every node.
4. The Service `web` has an address from **`172.30.0.0/28`**, and the router
   has learnt it as a **/32**.
5. From the router's network, the application **answers** at that address.

## The method, step by step

**Turn the BGP control plane on.** `helm upgrade cilium cilium/cilium
--version 1.20.5 -n kube-system --reuse-values --set
bgpControlPlane.enabled=true`, wait for the agents, then restart the operator:
it is the operator that creates the BGP CRDs (`kubectl get crd | grep bgp`).

**Declare the peer.** Three objects, in cluster scope, that reference each
other:

- a **`CiliumBGPClusterConfig`**: which nodes speak BGP (`nodeSelector`),
  with which local AS (`localASN: 65001`), to which peer (`peerAddress`,
  `peerASN: 65000`), and with which `peerConfigRef`;
- a **`CiliumBGPPeerConfig`**: the address family (`ipv4`, `unicast`), and
  the label of the advertisements to send to that peer;
- a **`CiliumBGPAdvertisement`** carrying that label: what to announce. One
  entry of type `PodCIDR`, one of type `Service` with the address type
  `LoadBalancerIP` and a `selector` on the Service's labels.

**Give addresses to LoadBalancer Services.** A **`CiliumLoadBalancerIPPool`**
with the block `172.30.0.0/28`. The Service `web` gets its address within
seconds.

**Label the nodes.** The `nodeSelector` of the cluster configuration picks
nodes by label: put that label on the three nodes. Without it, no session
starts, and no error says so.

**Check from your side.** `kubectl get ciliumbgpnodeconfigs` shows one
configuration per selected node. In an agent, `cilium-dbg bgp peers` shows
the session state and the number of routes sent. A wrong AS on one side
leaves the session in `Active`, and the router logs a `NOTIFICATION` (bad
peer AS).

## How you will know it works

The tests read the Cilium configuration, then ask the **router**: are the
three sessions established, which routes did it learn? Last, they request
the application from the router's network, at the LoadBalancer address,
through the route the router received.

```bash
dsoxlab check k8s-annoncer-un-service-en-bgp
```
