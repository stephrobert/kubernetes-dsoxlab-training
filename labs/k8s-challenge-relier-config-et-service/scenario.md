# Wire a ConfigMap, a Secret and a Service to a Deployment

## The situation

The shop runs on the kind cluster **`boutique`**, and your `kubectl` already
points at it. Its storefront must be shipped in a namespace of its own,
**`magasin`**, which does not exist yet. Nothing is in place: you create
everything.

The two images of the storefront, current version then next version:

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## What you must achieve

1. All the storefront objects are in the **`magasin`** namespace: the
   **`vitrine`** Deployment, the **`vitrine`** Service, the
   **`vitrine-config`** ConfigMap and the **`vitrine-secret`** Secret. None is
   created in `default`.

2. The **`vitrine`** Deployment has **three available replicas**.

3. The **`MESSAGE_ACCUEIL`** variable, which holds `Bienvenue` in the
   container, comes from the `vitrine-config` ConfigMap.

4. The **`DB_PASSWORD`** variable, which holds `Boutique-2026` in the
   container, comes from the `vitrine-secret` Secret, and the password **never
   appears in clear** in the Deployment.

5. The **`vitrine`** Service has **three ready endpoints** and answers HTTP at
   `http://vitrine.magasin` from a Pod of the cluster.

6. The storefront runs the **next version**: its three replicas are available
   on the new image, and the **previous ReplicaSet is kept at zero** replicas.

## How you are graded

The challenge is graded on the **state of the cluster**, never on the commands
typed: the configuration and the password are read from inside a Pod. The
pass mark is 70 out of 100. No step-by-step instructions: the lessons of the
module taught everything.

```bash
dsoxlab check  k8s-challenge-relier-config-et-service
dsoxlab submit k8s-challenge-relier-config-et-service
```
