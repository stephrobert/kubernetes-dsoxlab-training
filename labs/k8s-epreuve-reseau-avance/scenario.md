# Level 6 test: expose and protect a service on Cilium

## The situation

The shop moves its vitrine to the Cilium cluster of the `net-*` hosts:
`net-cp.lab`, `net-w1.lab`, `net-w2.lab`. Cilium 1.20.5 replaces kube-proxy.
Nobody touched it since the installation: no Gateway, no network policy, no
encryption, and the cluster has **no load balancer**.

In the space **`boutique`**:

- the **vitrine** answers HTTP behind the Service **`vitrine`** (port 80);
- **`caisse`** is its legitimate client;
- **`publicite`**, an ad tracker, reaches it too, and has no business there;
- **`relance`**, a reminder robot, carries the same labels as `caisse` and
  calls the vitrine in a loop. Besides reading it, it sends a request that a
  read-only vitrine must refuse. Which one, nobody remembers.

The certificate of `vitrine.formation.test` is ready in the Secret
**`vitrine-tls`**. It is signed by the shop's own authority, published in the
ConfigMap **`ca-boutique`**.

You work on `net-cp.lab`, with `kubectl` and `helm`. The Gateway API that
Cilium 1.20.5 supports is **v1.6.3**. For the addresses of exposed services,
the network team gives you **`172.31.0.0/28`**.

## What you must achieve

1. A **Gateway** served by Cilium in `boutique` is ready and has an address.
2. It serves `https://vitrine.formation.test/` with the certificate of
   `vitrine-tls`.
3. That name leads to the vitrine, and only that name.
4. Through the Gateway, the vitrine can be **read** (GET), and an attempt to
   **write** (POST) is **refused with a 403**.
5. `caisse` reads without writing; `publicite` cannot reach the vitrine at
   all.
6. The traffic between nodes is **encrypted with WireGuard**.
7. The ConfigMap **`diagnostic`** of `boutique` names the request that your
   protection refuses to `relance`: key **`methode`** (for example `DELETE`)
   and key **`chemin`** (for example `/panier`).

## Rules

No step-by-step and no hint: the course gave you the tools. The test is
passed at **70 %**. Two states can't be compensated by
the others: the read-only access through the Gateway (4) and the encryption
(6).

```bash
dsoxlab check k8s-epreuve-reseau-avance
```
