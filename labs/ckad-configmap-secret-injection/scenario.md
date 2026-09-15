# Inject configuration and secrets into a Pod

## The situation

The team ships the application **`app`** in the **`lab`** namespace. It reads
its configuration in two ways: **environment variables** for its simple
settings, and a **`config.yaml`** file it expects under `/etc/app-config`. It
also needs the credentials of its database, and the house rule is strict: **no
password in a Pod manifest**.

The namespace exists. Everything else is up to you.

## What you must achieve

1. A ConfigMap **`app-settings`** in `lab`, with `APP_MODE` set to
   `production`, `LOG_LEVEL` set to `info`, and a **`config.yaml`** key whose
   content includes the line `port: 8080`.

2. A Secret **`db-credentials`** in `lab`, with the keys **`DB_HOST`**, set to
   `db.internal.svc`, and **`DB_PASSWORD`**, whose value you choose.

3. A Pod **`app`** in `lab`, image `nginx:1.27-alpine`, which receives **all**
   the keys of `app-settings` as environment variables, which receives
   `DB_HOST` and `DB_PASSWORD` from the Secret, and which mounts
   `app-settings` under **`/etc/app-config`**.

4. From inside the container: `APP_MODE` is `production`, `DB_PASSWORD` is
   set, and `/etc/app-config/config.yaml` contains `port: 8080`.

## Useful bearings

There are two ways to inject a ConfigMap as variables: key by key, or as a
whole block. Same thing for a Secret. The Pod then carries only a
**reference**, never the value.

Mounted as a volume, a ConfigMap becomes a directory: each key is a file in
it. And unlike environment variables, a mounted file follows changes made to
the ConfigMap, with a delay.

## How you will know it works

The tests read the ConfigMap, the Secret and the Pod definition, then they
step into the container to read the variables and the file.

```bash
dsoxlab check ckad-configmap-secret-injection
```
