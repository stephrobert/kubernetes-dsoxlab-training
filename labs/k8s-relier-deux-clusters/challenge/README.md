# Challenge: Connect two clusters with Cilium ClusterMesh

## The situation

Two Kubernetes 1.37 clusters run **one node each**, without kube-proxy, with
Cilium 1.20.5:

| Cluster | Node | Pods | Cilium id |
|---|---|---|---|
| `cluster-1` | `ha-cp1.lab` | `10.241.0.0/16` | 1 |
| `cluster-2` | `ha-cp2.lab` | `10.242.0.0/16` | 2 |

They were installed to be connected: distinct Pod ranges and ids, the
**same Cilium certificate authority**, and the server `clustermesh-apiserver`
of each one exposed as a `NodePort`. They are **not connected** yet.

In each cluster, the namespace **`mesh-demo`** holds a Deployment `echo` that
answers with the name of **its** cluster, behind an ordinary Service `echo`.
In `cluster-1` only, a Pod **`client`** sleeps. Today, from `client`,
`echo.mesh-demo` always answers `reponse-de-cluster-1`.

You are on `ha-cp1.lab`. `kubectl` knows **two contexts**, `cluster-1`
(current) and `cluster-2`, and the CLI `cilium` (v0.20.3) is installed.

## What you must achieve

1. The Cilium agent of **each** cluster sees the node of the other one.
2. The Service `echo` of `mesh-demo` is **global** in **both** clusters.
3. From the Pod `client` of `cluster-1`, **both** clusters answer through the
   Service `echo`.

## The method, step by step

**Look before connecting.** `cilium clustermesh status --context cluster-1`
shows the state of the server `clustermesh-apiserver` and how it is exposed.
`kubectl --context cluster-1 -n kube-system exec ds/cilium -c cilium-agent --
cilium-dbg node list` lists the nodes the agent knows: only its own.

**Connect.** `cilium clustermesh connect --context cluster-1
--destination-context cluster-2` connects the two clusters **both ways**: it
gives each one the address and the certificates to reach the other. Then
`cilium clustermesh status --context cluster-1 --wait` waits until the
connection is up. The node list of each agent now shows the remote node,
prefixed with its cluster name.

**Make the Service global.** Connected clusters share their identities and
nodes, not their Services. The annotation `service.cilium.io/global: "true"`
on a Service with the **same name, in the same namespace,** in both clusters
merges their backends. Put it on both sides: on one side only, the other
cluster does not share its backends.

**Check from the client.** Several requests from `client` to
`http://echo.mesh-demo/` must return both `reponse-de-cluster-1` and
`reponse-de-cluster-2`. In an agent of `cluster-1`, `cilium-dbg service list`
shows the backends of the Service, the remote one included.

## How you will know it works

The tests read the node list of the agent in each cluster, the annotation of
the Service `echo` on both sides, then send twelve requests from `client` and
expect an answer from each cluster.

```bash
dsoxlab check k8s-relier-deux-clusters
```
