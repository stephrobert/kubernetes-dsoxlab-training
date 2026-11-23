# Challenge: install Gatekeeper, enforce a rule and read its audit

## 🧭 The situation

The warehouse team must now only run images that come from the
**`registry.k8s.io/`** registry. The rule must live in the cluster, and the
security team chose **Gatekeeper**, version **v3.23.1**. It is not installed
yet.

In the **`entrepot`** namespace, the **`ancien-stock`** Pod already runs with
an image from Docker Hub. The team wants to see it in a report before
migrating it: **do not delete it**.

The **`entrepot-temoin`** namespace is the control group. The rule must not
apply there.

## 🎯 What you must achieve

1. Gatekeeper **v3.23.1** runs in the `gatekeeper-system` namespace, with its
   controller and its audit ready.
2. In `entrepot`, a Pod whose image does not start with `registry.k8s.io/` is
   **refused** at creation by Gatekeeper. A Pod whose image comes from
   `registry.k8s.io/` is still accepted, and `entrepot-temoin` still accepts
   an image from Docker Hub.
3. The Gatekeeper **audit** reports `ancien-stock` as a violation of your
   rule.

## 🔎 Useful pointers

The lesson gives the installation through the release manifest: keep the
version pinned in the URL.

Gatekeeper splits a rule into two objects. The first one holds the logic in
Rego, and creates a new resource type. The second one applies that type to a
scope, with its parameters. The lesson shows an allowed-registries example:
read carefully how it compares the start of the image name.

The mode of the constraint decides what happens to a faulty Pod: only one of
the three modes refuses it.

Admission only checks new requests. For a Pod that was already running, look
at the `status` of your constraint: the audit writes what it finds there,
once a minute.

## ✅ How you will know it works

The tests read the Gatekeeper Deployments and their image. They then submit
real Pods to the API server, with `--dry-run=server`, using an image from
Docker Hub and an image from `registry.k8s.io/`, in both namespaces. Finally,
they read the `status` of your constraints to find `ancien-stock` there.

```bash
dsoxlab check k8s-imposer-des-regles-avec-gatekeeper
```
