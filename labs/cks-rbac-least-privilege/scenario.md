# Take cluster-admin back from a service account, without stopping its work

## The situation

In the **`equipe-dev`** namespace, the `portail-dev` application runs with the
**`dev-sa`** service account. That account is bound to **`cluster-admin`** by
the `dev-admin-binding` ClusterRoleBinding: someone needed it to work, and the
matter was forgotten.

Nothing is broken. That is exactly what makes this permission hard to take
back: nobody complains, and the day that account is compromised, the whole
cluster goes with it.

The audit asks that `dev-sa` be brought back to **the strict minimum**,
without breaking the application.

## What you must achieve

1. **`dev-sa` is no longer a cluster administrator.** The shortcut that gave
   it that power is gone.

2. **The account keeps enough to work in its namespace**: read and write the
   Pods, Deployments and Services of `equipe-dev`. Its application uses them,
   and must keep running.

3. **It can no longer read the Secrets** of its own namespace, including
   `jeton-de-paiement`.

4. **Its reach stops at its namespace.** It sees nothing in `kube-system`, nor
   anywhere else in the cluster.

5. The permission granted is **carried by the namespace**, not by a
   cluster-scoped object. A permission that applies everywhere is not a bounded
   permission.

## Useful bearings

A permission is not read in a manifest, it is **asked of the API server**.
`kubectl auth can-i` answers yes or no, and its `--as` option lets you ask
**on someone else's behalf**: that is how you check what an account can do
without connecting as it.

In an authorisation request, a service account is named
`system:serviceaccount:<namespace>:<name>`.

Two objects bind a subject to permissions, and the difference is exactly the
subject of this lab: one applies in **one** namespace, the other across the
**whole** cluster. Deleting the second and recreating it under another name
changes nothing.

## How you will know it works

The tests do not read your manifests: they put the questions to the API server
on behalf of `dev-sa`, and compare the answers. The one that counts checks
both directions in the same measurement: what the account must be able to do,
and what it must no longer be able to do. A permission taken from everyone
would fail just as much as one left whole.

```bash
dsoxlab check cks-rbac-least-privilege
```
