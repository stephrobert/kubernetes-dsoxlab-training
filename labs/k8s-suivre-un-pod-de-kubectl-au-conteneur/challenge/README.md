# Challenge: Follow a Pod from kubectl to the container

## 📍 The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your kubectl already targets it. The **`suivre-un-pod`** namespace is empty.
The **`~/suivre-un-pod/etapes.txt`** file waits for your answers: fill in the
value after each colon.

## 🎯 What you must achieve

1. A **`suivi`** Deployment, in the `suivre-un-pod` namespace, with **one
   available Pod**, on this image:

   ```text
   nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
   ```

2. After **`scheduled`**: the component that placed the Pod on a node.

3. After **`pulled`**, **`created`** and **`started`**: the component that
   downloaded the image, created the container and started it.

4. After **`noeud-du-kubelet`**: the node whose kubelet did that work.

## 🧭 Useful pointers

Each step of the path leaves an **event** on the Pod, and each event says which
component wrote it. `kubectl describe pod` lists them at the end, in order,
with a `From` column. `kubectl get events -o wide` shows the same events for
the whole namespace, with a `SOURCE` column.

The event's reason gives the step (`Scheduled`, `Pulled`, `Created`,
`Started`). The message of the `Scheduled` event gives the chosen node.

On this cluster, events are kept for **24 hours** (one hour by default in
Kubernetes). After a long break, those of the lab are gone: then run
`dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur` again.

## ✅ How you will know it is right

The tests read your Deployment and your file. They compare your answers with
the node that really runs the Pod.

```bash
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```
