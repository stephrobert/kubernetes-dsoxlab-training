# Challenge: Find, count and log refused flows

## 📍 The situation

In the **`livraison`** namespace of the Cilium cluster, four clients
(`preparation`, `expedition`, `facturation` and `retours`) call two services,
**`stock`** and **`tarif`**, every two seconds. The Pods are spread over
`net-w1.lab` and `net-w2.lab`. Since the last deployment, one client can no
longer reach one of the two services. Nobody knows which one, nor towards
what.

The security team does not want the network policies touched: it wants the
refusal **audited**. Another namespace of the cluster refuses flows too, and
it is not your concern.

You are on the control plane `net-cp.lab`, with `kubectl` and `helm`. The
cluster runs without kube-proxy, with Cilium 1.20.5, Hubble and its metrics
enabled (port 9965 of each node). Cilium 1.20.5 declares support for
Kubernetes 1.33 to 1.36, and this cluster runs 1.37.

## 🎯 What you must obtain

1. A ConfigMap **`refus`** in `livraison`, with three keys: **`source`**, the
   name of the refused client Pod, **`destination`**, the name of the Pod it
   can no longer reach, and **`noeud`**, the node whose Cilium agent sees the
   refusal. **Blocking requirement.**
2. On that node, the **`hubble_drop_total`** metric carries a series that
   names **both** the source Pod and the destination Pod of the refused flow,
   and it keeps growing: the refusal stays in place, and the refused client
   still reaches the service it is allowed. **Blocking requirement.**
3. On that same node, the refused flows of the `livraison` namespace are
   logged to **`/var/run/cilium/hubble/refus-livraison.log`**, and this file
   holds **nothing else**: neither other verdicts, nor the refusals of other
   namespaces.

## 🧭 Useful landmarks

A network policy does not always apply on the node of the destination.

## ✅ How you will know it works

The tests read your ConfigMap, the metrics port of the node of the refusal
twelve seconds apart, and the log exported on that node. The refused client,
its destination and so the node are drawn at random during the preparation.
The pass mark is 70%, that is all three requirements, and both blocking
requirements must be met.

```bash
dsoxlab check k8s-challenge-retrouver-les-flux-refuses
```
