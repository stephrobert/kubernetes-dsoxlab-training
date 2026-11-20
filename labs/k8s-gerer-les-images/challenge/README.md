# Challenge: Pin an image by digest and pull from a private registry

## 📍 The situation

The kind cluster **`lab`** is running on the machine, and your kubectl already
targets it. The **`galerie`** namespace runs two Deployments:

- **`affiche`** runs the **`nginx:1.30`** image, a tag whose content can
  change from one day to the next;
- **`vignettes`** pulls **`localhost:30500/galerie/vignettes:1.0`**, from a
  private registry that runs in the cluster, and does not start. Its
  ServiceAccount, **`vignettes`**, already carries a docker-registry Secret,
  set by a colleague.

The registry credentials: user **`galerie`**, password **`Vignettes-2026`**.
The **`~/galerie/`** directory is waiting for your record.

## 🎯 What you must obtain

1. **`affiche`** is **pinned by digest** on the image **it runs today**:
   neither another version nor a similar image. All its Pods run that digest.
2. **Before any repair**, **`~/galerie/releve.txt`** says on a **`cause:`**
   line why `vignettes` cannot pull its image: the request the registry
   refuses, and what it answers, as the event of the Pod gives them. After
   that, leave this file alone.
3. **`vignettes`** is available. Its credentials still come from a
   **docker-registry Secret carried by its ServiceAccount**, and are not
   written into the Pod.

## 🧭 Useful landmarks

A tag points to an image today; a digest points to it forever. The image a Pod
really runs is read in its status, not in its spec.

A Pod that cannot pull its image says why in its events. Read them before
correcting anything. A registry does not refuse a client that sends nothing
and a client that sends a wrong password in the same way. A docker-registry
Secret is read by decoding its `.dockerconfigjson` field.

The credentials of a private registry are given to a Pod, or to its
ServiceAccount. They are added when a Pod is created: a Pod that already
exists does not receive them.

## ✅ How you will know it works

The tests compare the digest of `affiche` with the one its Pods ran at the
start, read your record and compare its date with the birth of the running Pod
of `vignettes`, then check where the credentials of `vignettes` come from.

```bash
dsoxlab check k8s-gerer-les-images
```
