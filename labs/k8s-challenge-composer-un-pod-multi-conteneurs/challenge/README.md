# Challenge: Compose a multi-container Pod

## 📍 The situation

The photo team wants to publish its showcase on the kubeadm cluster, in the
**`photo`** namespace. The **`vitrine`** ConfigMap holds, under the
**`titre`** key, the title of the current exhibition. Nothing else exists. You
are on the control plane, with `kubectl` configured.

Images to use:

- server: `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`;
- helper tasks: `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

## 🎯 What you must obtain

A Deployment **`galerie`** with **two** replicas, each Pod bringing together
three containers:

1. an init container **`generer-page`**, which runs to the end before the
   others start and writes the home page, holding **the title of the
   `vitrine` ConfigMap**, into a **`page`** volume. Each Pod serves this page
   on its port 80. **Blocking requirement.**
2. a native sidecar **`relais-journaux`**, which starts before the server,
   runs alongside it and shows in **its own logs** every access the server
   receives. **Blocking requirement.**
3. the server **`serveur`**, which mounts the `page` volume **read-only**.

The server's access log goes through a temporary **`journaux`** volume,
capped at **32Mi**, mounted by the server and the sidecar, and by them only.

Both replicas are ready, with no restart at all.

## 🧭 Useful landmarks

The nginx image sends its access log to its standard output by default, not
to a file.

## ✅ How you will know it works

The tests read the Deployment and its Pods, load the page of each Pod, and
send a request to a path drawn at random, which must show up in the sidecar's
logs. The title is drawn at random during the preparation. The pass mark is
80%, and both blocking requirements must be met.

```bash
dsoxlab check k8s-challenge-composer-un-pod-multi-conteneurs
```
