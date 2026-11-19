# Challenge: Configure an application through ConfigMaps

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. The **`configuration`** namespace is empty.

## 🎯 What you must obtain

In the `configuration` namespace, with the values of the lesson:

1. A ConfigMap **`app-config`** carries `APP_MODE=production` and `LOG_LEVEL`.
   A Deployment **`app`** (busybox 1.38.0, sleeping) receives these two keys as
   **environment variables**, and `APP_MODE` can be read in the Pod.

2. A ConfigMap **`app-fichier`** carries a file **`app.properties`**, mounted
   **as a directory** on **`/etc/app`** in the container. After a change, this
   file says **`mode=maintenance`**, and the file read in the Pod is up to
   date.

3. `LOG_LEVEL`, first set to `info`, moves to **`debug`** in `app-config`. The
   Deployment is then **restarted**, and the Pod sees `debug`.

4. **No value** is written directly in the Deployment.

## 🧭 Useful landmarks

Create the ConfigMaps before the Deployment: `--from-literal` for values,
`--from-file` for a file, whose name becomes the key. Always check from the
container, with `kubectl exec deploy/app --`: the spec says what is asked, the
container says what is seen.

After a change, not everything is updated the same way:

- an environment variable is read when the container starts, then stays
  frozen;
- a volume mounted as a directory updates by itself, with a delay;
- a `subPath` mount is never updated.

Restarting the Deployment replaces the Pods, which read everything again.

## ✅ How you will know it is right

The tests read the ConfigMaps and the Deployment, then what the container sees.

```bash
dsoxlab check k8s-configurer-par-configmap
```
