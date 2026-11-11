# Deploy, expose and scale a first application

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. The **`demo-app`** namespace does not exist yet. The directory
**`~/demo-app/`** waits for the HTTP answer of your application.

## What you must obtain

1. In the **`demo-app`** namespace, a Deployment **`nginx`** runs the pinned
   image of the lesson:
   `nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.

2. `nginx` was created with **one replica**, then **scaled**: it now has
   **three available replicas**.

3. A ClusterIP Service **`nginx`** exposes it on port 80, and counts **three
   ready endpoints**.

4. **`~/demo-app/reponse.html`** holds the answer of `http://nginx`, read
   **from a client Pod** in the namespace.

## Useful landmarks

Create the namespace first, then work inside it: without `-n demo-app`, the
objects land in `default`. A Deployment creates a ReplicaSet, which creates the
Pods; the READY column of `kubectl get deployment` counts the ready Pods.

A Service does not check that it finds Pods: an empty endpoint list raises no
error. Compare its Selector with the labels of the Pods, and look at its
endpoints after scaling.

The name of a Service resolves inside the cluster, not on the machine. A
temporary Pod, started with an image that can make an HTTP request and removed
at the end, can query it; its output is redirected into a file like any other.

## How you will know it is right

The tests read the Deployment, the Service and its endpoints, then compare your
file with the page nginx really serves.

```bash
dsoxlab check k8s-premier-deploiement
```
