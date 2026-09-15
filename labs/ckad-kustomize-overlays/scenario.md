# One Kustomize base and two overlays, dev and prod

## The situation

The team deploys the same application into two namespaces, **`dev`** and
**`prod`**, and is tired of maintaining two sets of manifests that drift
apart. It wants a single **base**, and two **overlays** carrying only the
differences. Both namespaces already exist.

The application is a Deployment **`app`**, image `nginx:1.27-alpine`, and a
Service **`app-svc`** on port 80 that serves it.

## What you must achieve

1. In `dev`: a Deployment **`dev-app`** with **1** replica, whose Pods carry
   the label `env=dev`, and a Service **`dev-app-svc`** that has endpoints.

2. In `prod`: a Deployment **`prod-app`** with **3** replicas, whose Pods
   carry the label `env=prod`, and a Service **`prod-app-svc`** that has
   endpoints.

3. Both environments come from the **same base**: same image, same port, same
   structure, only the namespace, the replica count, the name prefix and the
   environment label differ.

## Useful bearings

`kubectl apply -k <directory>` applies a `kustomization.yaml`. An overlay
references the base in `resources`, and Kustomize knows how to prefix names,
set a namespace, add labels right down into the selectors, and change a
replica count, without touching the base.

The added label must also make it into the Service selector, otherwise the
Service no longer finds its Pods: Kustomize does that for you, if you ask it
to.

## How you will know it works

The tests read the Deployments, their Pods, the Services and their endpoints
in both namespaces, and compare the structure of the two environments.

```bash
dsoxlab check ckad-kustomize-overlays
```
