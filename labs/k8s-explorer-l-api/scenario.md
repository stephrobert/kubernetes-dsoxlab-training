# Explore the API with api-resources and explain

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the operations
team installed a **new resource type** to describe its backups, and you have **no
documentation**: the cluster's API is your only source. In the **`archives`**
namespace, the **`catalogue`** Deployment runs without a readiness probe. The
**`~/archives/`** directory is waiting for your record.

## What you must obtain

1. **`~/archives/releve.txt`** gives, on two `key: value` lines, what must be
   written in a manifest of this backup type:

   ```text
   apiversion: <group/version>
   kind: <Kind>
   ```

2. A backup named **`commandes-nuit`** exists in `archives`: it backs up the
   **`commandes`** database **every day at 2:00**. The names and the format of the
   fields are to be found in the API.

3. **`catalogue`** carries an **HTTP readiness probe** that queries the **root of
   port 80**, and its Pods are Ready.

4. The record has a third line, **`inventaire:`**, which names **every type of
   object present in `archives`**, separated by commas. Events are not required.

## Useful landmarks

The name of a group does not tell its version: the API gives it. A type you do
not know is discovered like a standard one, column by column, then field by field:
the `-required-` mark flags what an object cannot leave out, and the description
of a field tells its format.

The probe is found the same way, going down into the Deployment's Pod template.
Correct `catalogue` in place.

`kubectl get all` does not list everything a namespace holds. For the inventory,
query every type the API declares as listable in a namespace.

## How you will know it works

The tests compare your record with what the cluster's API declares, then read the
backup and the probe in the cluster.

```bash
dsoxlab check k8s-explorer-l-api
```
