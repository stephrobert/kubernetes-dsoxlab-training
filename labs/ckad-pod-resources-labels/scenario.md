# A two-container Pod with its resource budgets

## The situation

The team wants to ship into the **`lab`** namespace a Pod **`multi-app`**
carrying two containers: the web server, and a small collector running
alongside it. The cluster is shared, and the namespace rule is clear: every
container declares what it asks for and what it will not exceed.

## What you must achieve

1. A Pod **`multi-app`** in `lab`, `Running`, with exactly two containers.

2. The container **`web`**, image `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`, requests `100m` of CPU and `64Mi`
   of memory, and limits itself to `200m` and `128Mi`.

3. The container **`logger`**, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, runs in an endless loop,
   requests `50m` and `32Mi`, and limits itself to `100m` and `64Mi`.

4. In each container, **the memory limit the kernel enforces** is the one you
   declared.

## Useful bearings

Budgets are declared container by container, never at the Pod level. A memory
limit is not a wish: the kernel enforces it, and you can read it from inside the
container, in its cgroup.

`kubectl run` generates a single-container Pod; for two, you have to write the
YAML, and `--dry-run=client -o yaml` gives you a starting point.

## How you will know it works

The tests read the Pod definition, then they enter each container to read the
memory limit the kernel actually enforces.

```bash
dsoxlab check ckad-pod-resources-labels
```
