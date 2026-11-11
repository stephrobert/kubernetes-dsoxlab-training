# Create or apply: apply, server-side apply and prune

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the
**`livraisons`** namespace holds the **`suivi`** application, described in the
versioned folder **`~/livraisons/appli/`**: `suivi.yaml` at the root, the Service
and the ConfigMap in two subfolders. Only `suivi.yaml` has been applied so far.

- **`suivi`** runs **4 replicas**: an autoscaler decides it, and that number must
  no longer come from the file, which still sets `replicas: 2`.
- **`suivi-ancien`**, a ConfigMap applied long ago from this folder, no longer has
  a file there.
- **`journal`**, a ConfigMap applied from another folder, does not belong to the
  `suivi` application.
- **`tarifs`**, a Deployment created by `kubectl create`, passes under the
  responsibility of the pricing team, which drives it with server-side apply.

Version 2 of the image:

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## What you must obtain

1. **The whole `~/livraisons/appli/` folder is applied**, subfolders included.
2. **`suivi.yaml` no longer sets `replicas`**, `suivi` keeps its **4 replicas**,
   and **applying the file again keeps them** too.
3. **`tarifs`** runs **version 2**, and its image belongs to the
   **`equipe-tarifs`** field manager, through server-side apply.
4. **`suivi-ancien`** was removed by pruning, and **`journal`** still exists,
   untouched.

## Useful landmarks

`kubectl apply -f` on a folder does not go down into subfolders unless asked.

Removing a field from a file does not tell `apply` to leave it alone: `apply`
compares the file with the `last-applied-configuration` annotation, and a field
that disappeared from the file is a field to remove. Foresee what `apply` will do
before running it, for example with `--dry-run=server`.

Server-side apply assigns each field to a manager. Taking over a field another
manager owns causes a conflict, which the lesson explains.

`--prune` deletes what is no longer in the folder, among what it selects. Always
preview it before running it for real.

## How you will know it works

The tests read the annotations, simulate a new apply of `suivi.yaml` on the
server side, read the field managers of `tarifs`, and check what pruning removed
or spared.

```bash
dsoxlab check k8s-creer-ou-appliquer
```
