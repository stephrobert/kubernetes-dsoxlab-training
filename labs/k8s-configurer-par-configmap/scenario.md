# Configure an application through ConfigMaps

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. The **`configuration`** namespace is empty.

## What you must obtain

In the `configuration` namespace, starting from the values of the lesson:

1. A ConfigMap **`app-config`** holds `APP_MODE=production` and `LOG_LEVEL`. A
   Deployment **`app`** (busybox 1.38.0, sleeping) receives these two keys as
   **environment variables**, and `APP_MODE` reads inside the Pod.

2. A ConfigMap **`app-fichier`** holds a file **`app.properties`**, mounted
   **as a directory** on **`/etc/app`** in the container. After the change, it
   says **`mode=maintenance`**, and the file read inside the Pod is up to date.

3. `LOG_LEVEL`, first `info`, was changed to **`debug`** in `app-config`. The
   Deployment was then **restarted**, and the Pod sees `debug`.

4. **No value** is written directly in the Deployment.

## Useful landmarks

Create the ConfigMaps before the Deployment: `--from-literal` for values,
`--from-file` for a file, whose name becomes the key. Always prove it from the
container, with `kubectl exec deploy/app --`: the spec says what is requested,
the container says what is seen.

Not everything updates the same way after a change. An environment variable is
read when the container starts, and stays frozen. A volume mounted as a
directory refreshes on its own, with a delay. A `subPath` mount never
refreshes. Restarting the Deployment replaces the Pods, which read everything
again.

## How you will know it is right

The tests read the ConfigMaps and the Deployment, then what the container sees.

```bash
dsoxlab check k8s-configurer-par-configmap
```
