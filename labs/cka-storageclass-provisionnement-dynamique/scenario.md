# Create your StorageClass and get a volume no administrator created

## The situation

In the **`archives`** namespace, the **`donnees`** claim asks for 128Mi and stays
**Pending**. Nobody prepared a volume for it, and nobody will: the team that did
it by hand is gone.

The cluster now knows how to make them on demand: the **`local-path`** class is
installed. But it erases the volume when its claim disappears, and the archives
team wants to keep its data. It needs its own class.

## What you must achieve

1. A StorageClass **`garde`**, served by the **same provisioner** as
   `local-path`, which **keeps** its volumes when their claim disappears
   (`reclaimPolicy` **`Retain`**) and creates them only when a Pod uses the
   claim (`volumeBindingMode` **`WaitForFirstConsumer`**). The `local-path`
   class stays in place.

2. The `donnees` claim, which keeps its name, namespace and size, names the
   **`garde`** class.

3. It is **Bound**, and the volume it is bound to was **created for it** by the
   provisioner: nobody prepared it in advance.

4. That volume carries the **reclaim policy** `garde` imposes: **`Retain`**.

5. A Pod named **`registre`** mounts that claim on **`/data`**.

6. It writes a **`/data/temoin`** file there, in the volume.

## Useful bearings

Start by looking at what the cluster offers, and what the claim asks for. The
gap is there.

A StorageClass makes nothing itself: it designates a **provisioner** and passes
it its settings. Two classes can therefore share the same provisioner with
different policies. The existing class tells you which one to use.

The claim field at fault is currently an **empty string**, which is not the same
as an absent field: the empty string **explicitly disables** on-demand
provisioning. That field **cannot be changed** on an existing claim.

Do not be surprised it stays Pending right after your fix: a class in
`WaitForFirstConsumer` provisions **only when a Pod uses** the claim.

## How you will know it works

Each test checks one of the six states above. The first also checks that
`local-path` still exists: renaming the existing class is not creating one. The
third does not settle for seeing the claim Bound: it checks that the provisioner
created the volume for this claim. Creating a volume by hand, even with the
right class, would bind the claim too, without having provisioned anything on
demand. That is the neighbouring lab, not this one.

```bash
dsoxlab check cka-storageclass-provisionnement-dynamique
```
