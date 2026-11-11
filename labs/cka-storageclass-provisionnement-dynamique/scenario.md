# Get a volume nobody created, and see what becomes of it

## The situation

In the **`archives`** namespace, the **`donnees`** claim asks for 128Mi and stays
**Pending**. Nobody prepared a volume for it, and nobody will: the team that did
it by hand is gone.

The cluster, however, now knows how to make them on demand. You still have to
ask.

## What you must achieve

1. The `donnees` claim, which keeps its name and namespace, names the
   **`local-path`** class.

2. It is **Bound**, and the volume it is bound to was **created for it** by the
   provisioner of the class: nobody prepared it in advance.

3. That volume carries the **reclaim policy** its class imposes.

4. A Pod named **`registre`** mounts that claim on **`/data`**.

5. It writes a **`/data/temoin`** file there, in the volume.

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

Each test checks one of the five states above. The second does not settle for
seeing the claim Bound: it checks that the provisioner of the class created the
volume for this claim. Creating a volume by hand, even with the right class,
would bind the claim too, without having provisioned anything on demand. That is
the neighbouring lab, not this one.

```bash
dsoxlab check cka-storageclass-provisionnement-dynamique
```
