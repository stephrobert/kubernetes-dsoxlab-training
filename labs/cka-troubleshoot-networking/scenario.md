# Restore traffic to a Service

## The situation

In the **`lab`** namespace, the **`web-app`** Deployment runs two replicas, and
each of its Pods answers on its port 80. The **`web-svc`** Service is supposed
to serve them, and yet nothing gets through: the **`client`** Pod in the same
namespace, which queries it by its name, gets nothing.

Two things have happened since the last time it worked. A colleague "redid the
Service". And the security team put in place a **`block-all`** network policy,
which closes all incoming traffic in the namespace. That policy is
**intended**: it stays. It is up to you to reopen exactly what is needed, and
nothing more.

## What you must achieve

1. `web-svc` has **endpoints**, and they are the `web-app` Pods.

2. `web-svc` forwards traffic on the **port where nginx listens**.

3. An **`allow-web-ingress`** NetworkPolicy allows incoming traffic towards the
   **`app=web`** Pods on **port 80**, from any source. `block-all` is still
   there.

4. From the `client` Pod, `http://web-svc/` **answers**.

## Useful bearings

A Service is nothing but a selector and ports. A Service with no endpoint is a
selector that matches no Pod's labels. Endpoints but nothing getting through is
often a port. Everything correct and still nothing: a policy is blocking.

NetworkPolicy rules add up: a policy that closes everything and another that
opens a precise port give an open port. Nothing requires removing the first
one.

## How you will know it works

The tests read the Service's endpoints, its ports, both policies, and they
really make a request from the `client` Pod.

```bash
dsoxlab check cka-troubleshoot-networking
```
