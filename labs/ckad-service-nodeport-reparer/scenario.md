# Repair a NodePort Service

## The situation

In the **`guichet`** namespace, the **`accueil`** application runs with two
replicas, and each of its Pods answers its name, `accueil`, on its container
port. So that users outside the cluster can reach it, a colleague wrote a
Service **`accueil`** of type NodePort. Yet nobody reaches it.

The cluster has two nodes, **`k8s-cp.lab`** and **`k8s-w1.lab`**.

## What you must achieve

1. The Service `accueil` is of type **NodePort**, and its NodePort is
   **`30091`**, the address promised to users.

2. Its **endpoints** are the ready Pods of the `accueil` Deployment, reached on
   the **port their container listens on**.

3. `http://<address of k8s-cp.lab>:30091/` answers **`accueil`**.

4. `http://<address of k8s-w1.lab>:30091/` answers **`accueil`** too.

## Useful bearings

A Service is only a selector and ports. A Service without endpoints is a
selector matching no Pod's labels. Endpoints but nothing answering is often the
port it sends to.

A NodePort Service has **three** ports: the Service's own inside the cluster,
the container's one it sends to, and the one it opens on **every node**.
Without a declared value, Kubernetes draws the latter at random from its range.

Each node's address is read in the `INTERNAL-IP` column of
`kubectl get nodes -o wide`.

## How you will know it works

Each test checks one of the four states above. The last two make a real
request, one to the control plane, the other to the worker: a NodePort opens on
every node, wherever the Pods run.

```bash
dsoxlab check ckad-service-nodeport-reparer
```
