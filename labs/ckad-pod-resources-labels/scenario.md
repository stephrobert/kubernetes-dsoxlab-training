# A two-container Pod, with budgets, labels and an annotation

## The situation

The team wants to ship into the **`lab`** namespace a Pod **`multi-app`**
carrying two containers: the web server, and a small collector running
alongside it. The cluster is shared, and the namespace rule is clear: every
container declares what it asks for and what it will not exceed. The labels
serve the Services and the selections, the annotation serves the humans.

## What you must achieve

1. A Pod **`multi-app`** in `lab`, `Running`, with exactly two containers.

2. The container **`web`**, image `nginx:1.27-alpine`, requests `100m` of CPU
   and `64Mi` of memory, and limits itself to `200m` and `128Mi`.

3. The container **`logger`**, image `busybox:1.36`, runs in an endless loop,
   requests `50m` and `32Mi`, and limits itself to `100m` and `64Mi`.

4. The Pod carries the labels `app=multi-app`, `tier=frontend` and
   `version=v1`, and an annotation **`description`**, whose text you choose.

## Useful bearings

`resources` are declared container by container, never at the Pod level. A
memory limit is not a wish: the kernel enforces it, and you can read it from
inside the container.

`kubectl run` generates a single-container Pod; for two, you have to write the
YAML, and `--dry-run=client -o yaml` gives you a starting point.

## How you will know it works

The tests read the Pod definition, then they enter each container to read the
memory limit the kernel actually enforces.

```bash
dsoxlab check ckad-pod-resources-labels
```
