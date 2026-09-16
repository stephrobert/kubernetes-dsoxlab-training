# Pin an image by its digest, and prove the tag was not enough

## The situation

In the **`chaine`** namespace, the **`pinned-app`** Deployment runs two
replicas. Nothing is broken, and that is the problem: it refers to its image
by the `nginx:1.27-alpine` tag.

A tag is a **mutable name**. Whoever controls the registry can point it
somewhere else tomorrow, and the next Pod restart will pull a different image
under the same name, without a single manifest changing. The security audit
requires production images to be referenced **immutably**.

## What you must achieve

1. The `pinned-app` Deployment refers to its image by its **digest**, in the
   form `nginx@sha256:...`, and no longer by a tag.

2. The declared digest is **that of the image actually running**. A digest of
   the right shape but copied from elsewhere is worthless: that is exactly
   what the last test checks.

3. **Both replicas run** after the change. An immutable reference that stops
   the Pod from starting is not an improvement.

4. The namespace stays `chaine`, the Deployment keeps its name, and you do not
   change images: it is `nginx:1.27-alpine` that must be pinned, not another
   version.

## Useful bearings

The digest is not found in the manifest, it is asked of the node's **container
runtime**, or of the registry. The cluster runs containerd, and `docker` is
not installed: the image inspection commands are those of `crictl` and `ctr`.

Kubernetes itself writes what it actually resolved into each Pod's status,
under `status.containerStatuses[].imageID`. That is the most direct source,
and it does not lie: it is what the node runs.

Mind the shape. The `image` field expects `repository@sha256:<hex>`, and the
repository may be written `nginx` or `docker.io/library/nginx` depending on
what you read. Both are accepted as long as the digest is the right one.

## How you will know it works

The tests read the state of the cluster, never the commands you typed. The
last one compares the digest you **declared** with the one the node
**resolved**: it is the only one that tells a real pin from a string that
merely looks like a digest.

```bash
dsoxlab check cks-image-pinned-digest
```
