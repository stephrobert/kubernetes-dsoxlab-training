# Challenge: Change a live Deployment without losing a container, and resolve the drift

## The situation

In the namespace **`magasin`**, the Deployment **`web`** carries **two
containers**: the server `web` and a log agent `log-agent`. Its versioned
manifest, the "Git" version, is in your home directory:
**`~/magasin/web.yaml`**.

This morning, during a **load peak**, an operator raised `web` to **four
replicas** directly in the cluster, without touching the file. The peak is
still on. Then an incident was opened, reference **`INC-2026-0142`**, and the
team asks you for three live fixes.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. The container `web` runs
   **`nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`**,
   the container **`log-agent` is still there**, and the Deployment stays **the
   same object**: no deletion followed by a recreation.
2. The Deployment carries the annotation **`incident-ref=INC-2026-0142`**.
3. The container `log-agent` has the environment variable
   **`LOG_LEVEL=debug`**.
4. The **drift** is resolved: `kubectl diff -f ~/magasin/web.yaml` finds no gap
   anymore and returns code 0, and `web` still runs its **four replicas**.

## Landmarks

`kubectl patch` only touches the fields it names, and its type matters on
**lists**: strategic merge, the default, finds a container by its name; JSON
merge replaces the whole list with the one in the patch; JSON patch targets an
element by its index. `kubectl replace --force` deletes then recreates the
object: it stops every Pod at once.

Save the current state before changing anything. A change made in the cluster
without being reported into Git will be undone by the next `kubectl apply` of
the file. `kubectl diff -f` shows the gap, with `-` for the live value and `+`
for the file's; it is the file that must be updated, not the cluster that must
be rolled back.

## How you will know it works

The tests read the Deployment (image, containers, object identity, annotation,
variable), wait for the rollout to finish, then run `kubectl diff` on your
manifest.

```bash
dsoxlab check k8s-modifier-une-ressource-en-production
```
