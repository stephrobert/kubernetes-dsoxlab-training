# Route with the Gateway API, and see the Gateway declare itself programmed

## The situation

The same two applications as before live in the **`lab`** namespace and already
serve: the API and the site, behind `svc-api` and `svc-web`, on port `80`. One
hostname, **`app.local`**, for both.

This time the platform team decided to stop writing Ingress objects. It placed
in the cluster what is needed to use its successor, and leaves you to publish
your applications with it.

Each application answers with its own name, which lets you check unambiguously
which one replied.

## What you must achieve

For the `app.local` host:

1. An HTTP entry point exists, and the cluster declares it **programmed**. An
   entry point that is accepted but not programmed routes nothing.

2. Requests whose path starts with **`/api`** reach `svc-api`.

3. Requests whose path starts with **`/web`** reach `svc-web`.

4. A path you did not declare reaches **neither**.

The controller and its class are already in place, leave them alone. The HTTP
entry is exposed on the node's port **30080**.

## Useful bearings

What replaces Ingress is made of **two** objects, and that separation is the
point: the cluster operator owns the entry point, application teams attach
their routes to it.

```bash
kubectl get gatewayclass
kubectl api-resources --api-group=gateway.networking.k8s.io
```

The **port** declared by the entry point must match one of the controller's
entry points. Otherwise the object is accepted, shows up in `kubectl get`, and
is never programmed: nothing routes, and nothing says so but its
**conditions**.

A routing rule **with no match criteria** accepts everything arriving.

One field decides who may attach to the entry point. Both objects living here
in the same namespace, the most restrictive value is enough.

Requests are made by telling `curl` where to reach the host:

```bash
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api
```

## How you will know it works

The first test reads the entry point's **conditions**, not merely its
existence. The last queries all **three** paths, the third serving as control.

```bash
dsoxlab check cka-gateway-api-httproute
```
