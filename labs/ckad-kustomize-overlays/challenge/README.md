# Challenge: One Kustomize base and two overlays, recette and production

## 📍 The situation

The team deploys the **`catalogue`** application into two namespaces,
**`recette`** and **`production`**. It is tired of keeping two sets of
manifests that end up diverging. It wants a single **base**, and two
**overlays** that only hold the differences. Both namespaces exist and are
empty. The **`~/kustomize/`** directory waits for you, empty as well.

The application:

- a **`catalogue`** Deployment, with a **`web`** container on port **80**, in
  version 1:

  ```text
  version 1 : nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
  version 2 : nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
  ```

- a **`catalogue-svc`** Service on port 80, in front of it;
- a **`catalogue-config`** configuration, which gives the container two
  variables, **`MODE=lecture`** and **`ACCUEIL=Bienvenue`**. Kustomize
  generates it, and the container reads it through `envFrom`.

## 🎯 What you must obtain

1. The base is in **`~/kustomize/base/`**, the overlays in
   **`~/kustomize/overlays/recette/`** and
   **`~/kustomize/overlays/production/`**. Both overlays start from this
   **same base**.
2. In `recette`: **`rec-catalogue`** with **2** available replicas. In
   `production`: **`prd-catalogue`** with **4** available replicas.
3. The Pods of each environment carry the **`palier=recette`** or
   **`palier=production`** label. Each Service, **`rec-catalogue-svc`** and
   **`prd-catalogue-svc`**, finds the Pods of its environment.
4. Both environments have the same container and the same port.
5. **Only `recette` moves to version 2**, through its overlay. The base still
   describes version 1, and `production` stays on it.
6. Each container reads its configuration from a **generated ConfigMap**,
   whose name carries a hash of its content. In **production**, `MODE` is
   **`ecriture`**, and `ACCUEIL` keeps the value of the base. In recette,
   nothing changes.
7. The cluster **matches the folder**: comparing each overlay with the cluster
   shows no difference.

## 🧭 Useful landmarks

An overlay cites the base under `resources`, then only holds the differences:
namespace, name prefix, labels, replica count, image. The added label must
also go into the selector of the Service, otherwise the Service no longer
finds its Pods: Kustomize does it, if you ask it to.

A generator in the overlay can **replace** the one of the base, or **merge**
with it: only merging keeps the values the overlay does not cite. A generated
ConfigMap changes name when its content changes, which restarts the Pods that
read it. Never change the base for a single environment.

Look at what an overlay produces before applying it, then compare it with the
cluster.

## ✅ How you will know it is right

The tests read the Deployments, their Pods, the Services and their addresses,
the ConfigMaps, then compare your `~/kustomize/` folder with the cluster.

```bash
dsoxlab check ckad-kustomize-overlays
```
