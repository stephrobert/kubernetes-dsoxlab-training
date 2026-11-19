# Challenge: Create or apply: apply, server-side apply and prune

## 📍 The situation

The kind cluster **`lab`** is running on the machine, and your kubectl already
targets it. The **`livraisons`** namespace holds the **`suivi`** application.
Its files are in the **`~/livraisons/appli/`** folder: `suivi.yaml` at the
root, the Service and the ConfigMap in two subfolders. So far, only
`suivi.yaml` has been applied.

- **`suivi`** runs **4 replicas**. An autoscaler chooses this number: it must
  no longer come from the file, which still writes `replicas: 2`.
- **`suivi-ancien`** is a ConfigMap applied long ago from this folder. Its file
  is no longer there.
- **`journal`** is a ConfigMap applied from another folder. It does not belong
  to the `suivi` application.
- **`tarifs`** is a Deployment created by `kubectl create`. It is handed over to
  the pricing team, which drives it with server-side apply.

Version 2 of the image:

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## 🎯 What you must obtain

1. **The whole `~/livraisons/appli/` folder is applied**, subfolders included.
2. **`suivi.yaml` no longer writes `replicas`**, `suivi` keeps its
   **4 replicas**, and **also keeps them when the file is applied again**.
3. **`tarifs`** runs **version 2**, and its image belongs to the
   **`equipe-tarifs`** field manager, through server-side apply.
4. **`suivi-ancien`** was deleted by pruning (`--prune`), and **`journal`**
   still exists, untouched.

## 🧭 Useful landmarks

`kubectl apply -f` on a folder does not read subfolders unless you ask it to.

Removing a field from a file does not tell `apply` to leave it as it is.
`apply` compares the file with the `last-applied-configuration` annotation: a
field that disappeared from the file is a field to remove. Look at what `apply`
will do before running it, for example with `--dry-run=server`.

Server-side apply gives each field to a manager. Taking a field another manager
owns causes a conflict, which the lesson explains.

`--prune` deletes what is no longer in the folder, among the objects it
selects. Always simulate it before running it for real.

## ✅ How you will know it works

The tests read the annotations, simulate on the server side a new `apply` of
`suivi.yaml`, read the field managers of `tarifs`, and check what pruning
deleted or kept.

```bash
dsoxlab check k8s-creer-ou-appliquer
```
