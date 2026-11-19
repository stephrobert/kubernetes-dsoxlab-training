# Challenge: Explore the API with api-resources and explain

## 📍 The situation

The kind cluster **`lab`** is running on the machine, and your kubectl already
targets it. The operations team added a **new object type** to it, to describe
its backups. Nobody documented it for you: only the cluster can tell you how it
is written.

In the **`archives`** namespace, the **`catalogue`** Deployment runs without a
readiness probe. The **`~/archives/`** directory is waiting for your record.

## 🎯 What you must obtain

1. The file **`~/archives/releve.txt`** gives, on two lines in the
   `key: value` format, what goes at the top of a manifest of this backup type:

   ```text
   apiversion: <group/version>
   kind: <Kind>
   ```

2. A backup named **`commandes-nuit`** exists in `archives`. It backs up the
   **`commandes`** database **every day at 2:00**. It is up to you to find in
   the cluster the names of the fields and the expected format.

3. **`catalogue`** has an **HTTP readiness probe** that queries the **root
   (`/`) of port 80**, and all its Pods are Ready.

4. The record has a third line, **`inventaire:`**, which names **every type of
   object present in `archives`**, separated by commas. No need to include
   events.

## 🧭 Useful landmarks

The name of a group does not tell its version: `kubectl api-resources` gives
it. An unknown type is discovered like a known one: its line in
`api-resources`, then its fields with `kubectl explain`. The `-required-` mark
flags a mandatory field, and the description of a field tells its format.

The probe is found the same way, going down into the Deployment's Pod
template. Change `catalogue` itself, without deleting it.

`kubectl get all` does not show everything a namespace holds. For the
inventory, query every type the cluster declares as listable in a namespace.

## ✅ How you will know it works

The tests compare your record with what the cluster declares, then read the
backup and the probe in the cluster.

```bash
dsoxlab check k8s-explorer-l-api
```
