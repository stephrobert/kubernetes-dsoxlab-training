# Send a Pod's traffic out through an egress gateway

## The situation

The Cilium cluster of the `net-*` hosts has **three nodes**: `net-cp.lab`
(control plane), `net-w1.lab` and `net-w2.lab`. Cilium 1.20.5 replaces
kube-proxy, with the **egress gateway turned off** and masquerading done by
iptables.

In the namespace **`egress-demo`**, two Pods run on `net-w1.lab`:
**`sortie-controlee`** (label `app: sortie-controlee`) and **`autre`** (label
`app: autre`). A partner only accepts `sortie-controlee` from **one known
address**: the one of `net-w2.lab`.

A witness server runs **outside** the cluster, on another machine of the same
network. It answers with the source address it sees. Its URL is in the
ConfigMap **`temoin`** of `egress-demo`:
`kubectl -n egress-demo get configmap temoin -o jsonpath='{.data.url}'`.
Today, both Pods reach it from the address of `net-w1.lab`.

You are on `net-cp.lab`, with `kubectl` and `helm` configured.

## What you must achieve

1. The **egress gateway** and **BPF masquerading** are both on, and every
   Cilium agent is ready.
2. A **CiliumEgressGatewayPolicy** selects the Pod `sortie-controlee` of
   `egress-demo`, and not `autre`.
3. That policy covers the **witness's address** in its destinations, and
   designates **`net-w2.lab`**, and no other node, as gateway.
4. The witness sees `sortie-controlee` coming from **`net-w2.lab`**, and
   `autre` still from **`net-w1.lab`**.

## The method, step by step

**Turn the gateway on, with what it requires.** `helm upgrade cilium
cilium/cilium --version 1.20.5 -n kube-system --reuse-values --set
egressGateway.enabled=true --set bpf.masquerade=true`. Both values go
together: with the gateway alone, the agent stops at startup with
`level=fatal`, and the DaemonSet stays half rolled out. Wait for the agents,
then restart the operator so that it reads the new configuration
(`kubectl -n kube-system rollout restart deployment/cilium-operator`).
`cilium status` in an agent must show `Masquerading: BPF`.

**Designate the gateway node.** A policy does not name a node: it selects
nodes by label. Put a label on `net-w2.lab` (for example
`egress-gateway=true`).

**Write the policy.** A `CiliumEgressGatewayPolicy` (cluster scope) has three
parts: `selectors` (a `podSelector` with the Pod's label `app` and its
namespace through the label `io.kubernetes.pod.namespace`),
`destinationCIDRs` (the witness's address in `/32`), and `egressGateway` (the
`nodeSelector` of the gateway, and the interface `enp1s0`).

**Check from outside.** `kubectl -n egress-demo exec sortie-controlee -- wget
-qO- -T 5 <url>` returns the source the witness saw. In an agent,
`cilium-dbg bpf egress list` shows what the datapath learnt: the gateway node
holds the egress address, the others forward to it. If the gateway node loses
its label, the selected Pod does not fall back to its own node: its requests
time out.

## How you will know it works

The tests read the Cilium configuration and the policies, then make both
Pods reach the witness: `sortie-controlee` must arrive from `net-w2.lab`, and
`autre` from `net-w1.lab`.

```bash
dsoxlab check k8s-faire-sortir-le-trafic-par-une-passerelle
```
