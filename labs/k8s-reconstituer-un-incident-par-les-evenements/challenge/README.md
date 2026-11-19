# Challenge: Rebuild an incident from the Events of a namespace

## The situation

A few minutes ago, the online shop started answering badly. Five applications
run in the namespace **`boutique`**: **`panier`**, **`paiement`**,
**`catalogue`**, **`stock`** and **`avis`**. According to the team, several of
them went down, one after the other.

Before anyone repairs anything, you are asked for the **incident report**.
**Do not repair anything**: the report describes what happened.

You are on the control plane, with `kubectl` configured.

## What you must achieve

A ConfigMap **`rapport`** in the namespace `boutique`, with:

1. **one key per application** (`panier`, `paiement`, `catalogue`, `stock`,
   `avis`). Its value is the **reason** of its `Warning` Events, written word
   for word; for an application that has **no** `Warning` Event, the value is
   **`aucune`**;
2. a key **`premiere-touchee`**: the name of the application concerned by the
   **first** `Warning` Event of the namespace.

## Landmarks

An Event concerns a precise object: here, the Pods. The name of a Pod of a
Deployment starts with the name of the Deployment.

`kubectl events` filters by type (`--types`) and by object (`--for`).
`kubectl get events` filters by field (`--field-selector`) and sorts
(`--sort-by`). The same Event exists in two representations, `v1` and
`events.k8s.io/v1`, whose field names differ: a sort or a `jsonpath` written
for one does not necessarily work on the other.

Events only live **one hour**: after that, they disappear.

## How you will know it works

The tests derive the fault of each application from its spec, read the Warning
Events of the namespace themselves to find the first one, then compare with
your report.

```bash
dsoxlab check k8s-reconstituer-un-incident-par-les-evenements
```
