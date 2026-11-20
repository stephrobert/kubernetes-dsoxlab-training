# Challenge: Write and validate a manifest

## 📍 The situation

The kind cluster **`lab`** is running on the machine, and your kubectl already
targets it. The orders team hands you its **`api`** application. A colleague
wrote its manifest, **`~/commandes/api.yaml`**: a single file, with an
**`api-config`** ConfigMap, an **`api`** Deployment and an **`api`** Service.
They never managed to apply it in full.

In the **`commandes`** namespace, an **old version** of the `api` Deployment
is running: one replica, an old image, without configuration.

The image of the application:

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

## 🎯 What you must obtain

1. **`~/commandes/api.yaml`** still holds the three objects in a single file,
   and the **server** accepts it as is.
2. Each of the three objects **writes the `commandes` namespace in the file
   itself**. Nothing of the application must be in `default`.
3. **`api`** has **2 available replicas**, with a container on port **80**, on
   the image above.
4. The **`api`** Service, on port **80**, finds both Pods.
5. The container receives **`DEVISE=EUR`** from the **`api-config`**
   ConfigMap, through `envFrom`.
6. The running `api` Deployment is **updated in place**: an `api` deleted then
   recreated does not count.

## 🧭 Useful landmarks

The file has several mistakes. Some show when you read it, only one is
reported by the server, and another produces no error at all: read again what
the cluster created, not only what kubectl prints.

An object that does not name its namespace goes to the one of the current
context. A Service finds its Pods by their labels.

Applying a manifest updates the objects that already exist, without recreating
them.

## ✅ How you will know it is right

The tests read your file, have it validated by the server, then read in the
cluster what it created, and the state of the `api` Deployment.

```bash
dsoxlab check k8s-ecrire-un-manifeste
```
