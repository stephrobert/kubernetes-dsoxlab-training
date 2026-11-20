# Challenge: Explore the API with api-resources and explain

## 📍 The situation

The kind cluster **`lab`** is running on the machine, and your kubectl already
targets it. The data team added a **new type of object** to it, to describe
its database exports. Nobody documented it for you: only the cluster can tell
you how it is written.

In the **`entrepot`** namespace, the **`annuaire`** Deployment runs without a
readiness probe. The **`~/entrepot/`** directory waits for your record.

## 🎯 What you must obtain

1. The file **`~/entrepot/releve.txt`** gives, on two lines in the
   `key: value` format, what is written at the top of a manifest of this
   export type:

   ```text
   apiversion: <group/version>
   kind: <Kind>
   ```

2. An export named **`ventes-hebdo`** exists in `entrepot`. It exports the
   **`ventes`** database **in parquet format**, **every Monday at 3:30**. It
   is up to you to find in the cluster the name of the fields and the
   expected format.

3. **`annuaire`** has an **HTTP readiness probe** that queries the
   **`/healthz`** path on the **port named `web`** of its container, and all
   its Pods are Ready.

4. The record has a third line, **`inventaire:`**, that names **every type of
   object present in `entrepot`**, separated by commas. No need to put the
   events in it.

## 🧭 Useful landmarks

A type can be served in several versions, which do not necessarily have the
same fields. The name of a group does not tell its version: `kubectl
api-resources` gives the one the cluster serves. An unknown type is discovered
like a known one: its line in `api-resources`, then its fields with `kubectl
explain`. The `-required-` mark flags a required field, an `enum:` line the
only allowed values, and the description of a field gives its format.

The probe is found the same way, going down into the Pod template of the
Deployment. Change `annuaire` itself, without deleting it.

`kubectl get all` does not show everything a namespace holds. For the
inventory, query every type that the cluster declares listable in a namespace.

## ✅ How you will know it is right

The tests compare your record with what the cluster declares, then read the
export and the probe in the cluster.

```bash
dsoxlab check k8s-explorer-l-api
```
