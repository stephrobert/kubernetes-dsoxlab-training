# Challenge: Repair a NodePort Service

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`guichet`** namespace, the **`accueil`** application runs
in two Pods. Each one answers its name, `accueil`, on its container port.

So that users outside the cluster can reach it, a colleague wrote a NodePort
Service named **`accueil`**. Yet nobody reaches it.

The cluster has two nodes, **`k8s-cp.lab`** and **`k8s-w1.lab`**.

## 🎯 What you must obtain

1. The `accueil` Service is of type **NodePort**, and its node port is
   **`30091`**: that is the address promised to the users.

2. Its **endpoints** are the ready Pods of the `accueil` Deployment, reached on
   the **port their container listens on**.

3. `http://<address of k8s-cp.lab>:30091/` answers **`accueil`**.

4. `http://<address of k8s-w1.lab>:30091/` answers **`accueil`** too.

## 🧭 Useful landmarks

A Service is a selector and some ports. No endpoint: the selector matches the
labels of no Pod. Endpoints, but nothing answers: it is often the port it sends
to.

A NodePort Service has **three** ports: the Service port inside the cluster,
the container port it sends to, and the one it opens on **every node**. If you
do not give the last one, Kubernetes picks it at random in its range.

The address of each node shows in the `INTERNAL-IP` column of
`kubectl get nodes -o wide`.

## ✅ How you will know it is right

Each test checks one of the four requirements above. The last two send a real
request, one to the control plane, the other to the worker: a NodePort opens on
every node, wherever the Pods run.

```bash
dsoxlab check ckad-service-nodeport-reparer
```
