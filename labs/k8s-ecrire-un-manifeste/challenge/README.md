# Challenge: Write and validate a manifest

## 📍 The situation

The kind cluster **`lab`** is running on the machine, and your kubectl already
targets it. The orders team hands you its **`api`** application: it must be
described in a manifest, a file you keep in Git.

The **`commandes`** namespace exists. It already holds a **`rapport`**
Deployment that does not start. The **`~/commandes/`** directory is empty.

The image of the application, which is also the one `rapport` must use:

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

## 🎯 What you must obtain

1. **`~/commandes/api.yaml`** is **a single file** that holds three objects: a
   ConfigMap **`api-config`**, a Deployment **`api`** and a Service **`api`**.
   The server accepts it as it is.
2. Each of these objects **writes the `commandes` namespace in the file
   itself**. Nothing from the application must be in `default`.
3. **`api`** has **2 available replicas**, with a container on port **80**, on
   the image above.
4. The **`api`** Service, on port **80**, finds both Pods.
5. The container receives **`DEVISE=EUR`** from the **`api-config`** ConfigMap,
   through `envFrom`.
6. **`rapport`** runs with **3 available replicas** on the image above. It is
   **fixed in place**: a `rapport` deleted then recreated does not count.

## 🧭 Useful landmarks

Do not start from a blank page: kubectl can generate the skeleton of an object
without creating anything. Complete it, then have the server validate the file
before applying it: kubectl alone does not see every error.

An object that does not name its namespace goes to the one of the current
context. A file can hold several objects, separated by a `---` line.

An existing object can be fixed without deleting it: there are several ways to
do it.

## ✅ How you will know it works

The tests read your file, have the server validate it, then read in the
cluster what it created, and the state of `rapport`.

```bash
dsoxlab check k8s-ecrire-un-manifeste
```
