# Require mTLS in a mesh, and prove it with a client left outside

## The situation

An application runs inside an Istio service mesh. Each of its Pods carries a
sidecar, and traffic between them **can** be encrypted.

Can, only. The audit has just shown it: any Pod in the cluster, one that does
not belong to the mesh and therefore presents no workload certificate, reaches
the service without trouble and reads its response in the clear. The mesh was
installed, but nothing was ever **required** of it.

You have three Pods. In the **`maillage`** namespace, which receives the
sidecars: **`service`**, serving a page, and **`client-maille`**, calling it.
In the **`dehors`** namespace, with no sidecar: **`client-nu`**.

## What you must achieve

1. The `maillage` namespace no longer accepts anything but mutually
   authenticated traffic, whatever its origin.

2. `client-nu`, from `dehors`, **no longer reaches** `service`.

3. `client-maille` **still reaches** `service`. The application must not go
   down: you are not asked for an outage, you are asked for a requirement.

Install and uninstall nothing: the mesh is already there.

## Useful bearings

What governs the **inbound** traffic a mesh Pod accepts is an Istio object,
not a native Kubernetes one: neither NetworkPolicy nor Ingress.

That object has a **mode**. The one in force by default accepts encrypted and
plain traffic alike, and exists to migrate an application without cutting it.
Another accepts only mutual TLS.

It is placed in the namespace of the **called** service, not the caller's.

With no `selector` field, it applies to the whole namespace; with a
`selector`, only to the Pods it designates.

The rule reaches the sidecars through istiod. It does not take effect the
second the API accepts the object: give it a few seconds.

## How you will know it works

The last test exercises **both sides**: it waits for `client-nu` to be
blocked, then checks that `client-maille` still gets through. An object left
in permissive mode would let both through; a misplaced requirement would block
both. Neither counts as a pass.

```bash
dsoxlab check cks-istio-mtls-lockdown
```
