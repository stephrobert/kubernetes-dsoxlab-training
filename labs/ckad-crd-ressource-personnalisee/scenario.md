# Use a custom resource, read its schema refusals, unblock it

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the
operations team installed a CRD that describes **backups**: the kind
**`Sauvegarde`**. No operator watches it yet. In the namespace
**`sauvegardes`**, there are two resources:

- **`hebdomadaire`**, which keeps its backups for **14 days**;
- **`ancienne`**, which someone deleted and which is still listed, in
  **Terminating**.

The directory **`~/sauvegardes/`** waits for what you will read from the API.

## What you must achieve

1. A Sauvegarde **`quotidienne`** in `sauvegardes`, with source
   **`donnees-registre`**, kept **7 days**.
2. **`hebdomadaire`** now keeps **30 days**, **without having been
   recreated**.
3. **`~/sauvegardes/api.txt`** gives the **API group and version** that serve the
   kind Sauvegarde, in the form `group/version`.
4. **`~/sauvegardes/refus.txt`** holds the **message of the API** that refuses a
   Sauvegarde kept **400 days**. This request is refused: it creates nothing.
5. **`ancienne`** is gone, **without** the CRD or the other resources having been
   deleted.

## Useful bearings

A CRD adds a kind to the API, in a group and a version of its own. The list of
the resources the API serves, and the explanation of their fields, are read as
for a native kind.

A custom resource is created, read, modified and deleted like a native object.
Its fields follow the **schema** of the CRD: a wrong type or a value out of the
bounds is refused by the API, which says why.

A resource that stays in Terminating waits for its **finalizers** to be removed.
Usually its controller does it. Here there is none. Deleting the CRD would
unblock the resource, but would take all the others with it.

## How you will know it works

Each test checks one of the five states above. For `hebdomadaire` and for the
CRD, it compares their identifier with the one of the start. For the refusal, it
reads your file again, then checks that the API still refuses a retention of 400
days.

```bash
dsoxlab check ckad-crd-ressource-personnalisee
```
