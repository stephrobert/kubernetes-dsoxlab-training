# Pin an image by digest and pull from a private registry

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the
**`galerie`** namespace runs two Deployments:

- **`affiche`** runs the **`nginx:1.30`** image, a tag whose content can change
  overnight;
- **`vignettes`** pulls **`localhost:30500/galerie/vignettes:1.0`**, from a private
  registry served in the cluster, and does not start. Its ServiceAccount is named
  **`vignettes`**.

The registry credentials: user **`galerie`**, password **`Vignettes-2026`**. The
**`~/galerie/`** directory is waiting for your record.

## What you must obtain

1. **`affiche`** is **pinned by digest** on the image **it runs today**, neither
   another version nor a neighbouring image, and all its Pods run that digest.
2. **Before any repair**, **`~/galerie/releve.txt`** says on a **`cause:`** line
   why `vignettes` cannot pull its image: what the registry expects and does not
   receive. Then leave it untouched.
3. **`vignettes`** is available: its credentials come from a **docker-registry
   Secret carried by its ServiceAccount**, not written into the Pod.

## Useful landmarks

A tag points to an image today; a digest points to it forever. The image a Pod
really runs is read in its status, not in its spec.

A Pod that cannot pull its image says why in its events. Read them before
correcting anything.

The credentials of a private registry are given to a Pod, or to its
ServiceAccount. They are injected when a Pod is created: a Pod that already
exists does not receive them.

## How you will know it works

The tests compare the digest of `affiche` with the one its Pods ran at the start,
read your record and its date, then check where the credentials of `vignettes`
come from.

```bash
dsoxlab check k8s-gerer-les-images
```
