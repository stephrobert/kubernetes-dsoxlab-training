# Challenge: One Kustomize base and two overlays, dev and prod

## 📍 The situation

The team deploys the same application into two namespaces, **`dev`** and
**`prod`**. It is tired of keeping two sets of manifests that drift apart. It
wants a single **base**, and two **overlays** that hold only the differences.
Both namespaces exist and are empty. The **`~/kustomize/`** directory is
waiting for you, empty as well.

The application:

- a Deployment **`app`**, with a container **`web`** on port **80**, at
  version 1:

  ```text
  version 1: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
  version 2: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
  ```

- a Service **`app-svc`** on port 80, in front of it;
- a configuration **`app-config`**, which gives the container the variable
  **`MESSAGE=Bienvenue`**. Kustomize generates it, and the container reads it
  through `envFrom`.

## 🎯 What you must obtain

1. The base lives in **`~/kustomize/base/`**, the overlays in
   **`~/kustomize/overlays/dev/`** and **`~/kustomize/overlays/prod/`**. Both
   overlays come from this **same base**.
2. In `dev`: **`dev-app`** with **1** available replica. In `prod`:
   **`prod-app`** with **3** available replicas.
3. The Pods of each environment carry the label **`env=dev`** or
   **`env=prod`**. Each Service, **`dev-app-svc`** and **`prod-app-svc`**,
   finds the Pods of its own environment.
4. Both environments have the same container and the same port.
5. **Only `dev` moves to version 2**, through its overlay. The base still
   describes version 1, and `prod` stays on it.
6. Each container reads its configuration from a **generated ConfigMap**,
   whose name carries a hash of its content.
7. The cluster **matches the folder**: comparing each overlay with the cluster
   shows no difference.

## 🧭 Useful landmarks

An overlay names the base in `resources`, then holds only the differences:
namespace, name prefix, labels, number of replicas, image. The added label must
also go into the Service's selector, otherwise the Service no longer finds its
Pods: Kustomize does it, if you ask it to.

A generated ConfigMap changes its name when its content changes, which restarts
the Pods that read it. Never change the base for one environment only.

Look at what an overlay produces before applying it, then compare it with the
cluster.

## ✅ How you will know it works

The tests read the Deployments, their Pods, the Services and their endpoints,
the ConfigMaps, then compare your `~/kustomize/` folder with the cluster.

```bash
dsoxlab check ckad-kustomize-overlays
```
