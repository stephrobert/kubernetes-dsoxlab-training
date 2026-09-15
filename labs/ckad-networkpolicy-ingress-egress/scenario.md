# Partition three tiers with ingress and egress NetworkPolicy

## The situation

In the **`lab`** namespace, a classic three-tier application:
**`frontend`**, **`backend`** and **`database`**, three Pods labelled
`tier=frontend`, `tier=backend` and `tier=database`. The last two serve HTTP
on port **80**. Today everything talks to everything, and a fourth Pod,
**`intrus`**, with no label at all, reaches the database without any
trouble.

The security team wants only the intended flows to exist: the frontend talks
to the backend, the backend talks to the database and resolves names, and the
database talks to nobody.

## What you must achieve

1. A NetworkPolicy **`backend-policy`** on the `tier=backend` Pods that
   allows inbound traffic only from `tier=frontend` Pods on port 80, and
   outbound traffic only to `tier=database` Pods on port 80, plus the cluster
   **DNS**, port 53 over UDP and TCP.

2. A NetworkPolicy **`database-policy`** on the `tier=database` Pods that
   allows inbound traffic only from `tier=backend` Pods on port 80, and
   **no outbound traffic at all**.

3. For real: `frontend` reaches `backend`, `backend` reaches `database` and
   resolves names, `intrus` reaches neither `backend` nor `database`, and
   `database` reaches nothing, not even DNS.

## Useful bearings

A NetworkPolicy only states what it allows, in the directions it declares
under `policyTypes`. Declaring `Egress` with no `egress` rule forbids all
outbound traffic; not declaring `Egress` says nothing about outbound traffic.

A Pod whose egress is restricted loses DNS unless you allow it explicitly:
the cluster resolver lives in `kube-system`, and it listens on port 53 over
UDP and over TCP.

## How you will know it works

The tests read the two policies, then make real connections between the Pods,
the ones that must go through and the ones that must fail.

```bash
dsoxlab check ckad-networkpolicy-ingress-egress
```
