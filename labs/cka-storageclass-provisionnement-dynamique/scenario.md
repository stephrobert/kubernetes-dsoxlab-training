# Get a volume nobody created, and see what becomes of it

## The situation

In the **`archives`** namespace, the **`donnees`** claim asks for 128Mi and stays
**Pending**. Nobody prepared a volume for it, and nobody will: the team that did
it by hand is gone.

The cluster, however, now knows how to make them on demand. You still have to
ask.

## What you must achieve

1. The `donnees` claim is **Bound**, and the volume it is bound to was
   **created for it**: nobody prepared it in advance.

2. A Pod named **`registre`** mounts that claim on `/data` and writes a
   **`/data/temoin`** file there.

3. The claim keeps its name and namespace.

## Useful bearings

Start by looking at what the cluster offers, and what the claim asks for. The
gap is there.

The field at fault is currently an **empty string**, which is not the same as an
absent field: the empty string **explicitly disables** on-demand provisioning,
while an absent field lets the cluster's default class apply.

That field **cannot be changed** on an existing claim.

Do not be surprised it stays Pending right after your fix: this cluster's class
provisions **only when a Pod uses** the claim. `kubectl get storageclass` shows
it in its `VOLUMEBINDINGMODE` column.

Finally, look at what you got **without asking**: a volume, with a policy the
class imposes on it, which decides its fate the day the claim disappears.

## How you will know it works

The last test does not settle for seeing the claim Bound: it checks the volume
belongs to the class, and carries its policy. Creating a volume by hand would
bind the claim too, without having provisioned anything on demand. That is the
neighbouring lab, not this one.

```bash
dsoxlab check cka-storageclass-provisionnement-dynamique
```
