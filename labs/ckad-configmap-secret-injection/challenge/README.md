# Challenge: Inject configuration and secrets into a Pod

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. The team ships the **`app`** application in the **`lab`**
namespace. It reads its configuration in two ways:

- **environment variables**, for its simple settings;
- a **`config.yaml`** file, which it expects in `/etc/app-config`.

It also needs the credentials of its database. The house rule is strict: **no
password in a Pod manifest**.

The namespace exists. Everything else is to be done.

## 🎯 What you must obtain

1. A ConfigMap **`app-settings`** in `lab`, with `APP_MODE` set to
   `production`, `LOG_LEVEL` set to `info`, and a **`config.yaml`** key whose
   content includes the line `port: 8080`.

2. A Secret **`db-credentials`** in `lab`, with the keys **`DB_HOST`**, set to
   `db.internal.svc`, and **`DB_PASSWORD`**, whose value you choose.

3. A Pod **`app`** in `lab`, image `nginx:1.30.6`, which:
   - receives **every** key of `app-settings` as environment variables;
   - receives `DB_HOST` and `DB_PASSWORD` from the Secret;
   - mounts `app-settings` in **`/etc/app-config`**.

4. From inside the container: `APP_MODE` is `production`, `DB_PASSWORD` is
   set, and `/etc/app-config/config.yaml` contains `port: 8080`.

## 🧭 Useful landmarks

A ConfigMap is injected as variables in two ways: key by key, or as a block. So
is a Secret. The Pod then only holds a **reference**, never the value.

Mounted as a volume, a ConfigMap becomes a directory, where each key is a file.
Unlike environment variables, a mounted file follows the changes of the
ConfigMap, with a delay.

## ✅ How you will know it is right

The tests read the ConfigMap, the Secret and the Pod definition. They then step
into the container to read the variables and the file.

```bash
dsoxlab check ckad-configmap-secret-injection
```
