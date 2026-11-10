# Follow a Pod from kubectl to the container

## The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your `kubectl` already points at it. The **`suivre-un-pod`** namespace is
empty, and the survey **`~/suivre-un-pod/etapes.txt`** waits for your answers:
fill in the value after each colon.

## What you must achieve

1. A **`suivi`** Deployment in the `suivre-un-pod` namespace, with **one
   available replica**, on this image:

   ```text
   nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
   ```

2. **`scheduled`** names the component that placed the Pod on a Node.

3. **`pulled`**, **`created`** and **`started`** name the component that
   pulled the image, created the container and started it.

4. **`noeud-du-kubelet`** names the Node whose kubelet did that work.

## Useful pointers

Once the Deployment is created, the API server has only stored a wish. Each
step that follows leaves an **event** on the Pod, and each event says which
component wrote it: `kubectl describe pod` lists them at the bottom, in the
order they happened, with a **From** column. `kubectl get events -o wide` shows
the same events for the whole namespace, with a SOURCE column.

The reason of the event gives the step (`Scheduled`, `Pulled`, `Created`,
`Started`); the message of the `Scheduled` event names the Node chosen.

Events are kept for **24 hours** on this cluster (one hour is the Kubernetes
default). After a longer break, those of the lab are gone: `dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur`
lays the situation out again.

## How you will know it is right

The tests read your Deployment and your survey, and compare the survey with
the Node that actually runs the Pod.

```bash
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```
