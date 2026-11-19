# Challenge: Create a multi-node kind cluster

## 📍 The situation

On the `k8s-kind.lab` machine, Docker, kind and kubectl are installed, and
your account is allowed to use Docker. To leave you enough memory, **the lab
deleted the clusters of the other labs** (`lab`, `boutique`, `architecture`).
You broke nothing: each lab recreates its cluster when you start it. The
**`~/atelier/`** directory is empty.

## 🎯 What you must obtain

1. A **`~/atelier/kind-atelier.yaml`** file that describes a kind cluster of
   **three nodes: one control plane and two workers**.

2. A kind cluster named **`atelier`**, created from that file.

3. Its **three nodes are `Ready`**, on Kubernetes **`v1.37.0`**, with the node
   image of the course:
   `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5`.

4. The roles are right: **one control plane and two workers**.

## 🧭 Useful landmarks

A cluster of several nodes is described in a file. The lesson gives its shape:
a `nodes` list, with a `role` for each node.

The node image does not go in the file. Give it to `kind create cluster`, with
the cluster name and the path of the file. Careful: without a name, kind calls
the cluster `kind`.

A cluster that answers is not necessarily ready. Count the nodes and read the
`STATUS` and `VERSION` columns of `kubectl get nodes`. Wait until all three are
`Ready`. For a worker, the `ROLES` column shows `<none>`: that is expected.

## ✅ How you will know it is right

The tests read your file, then query the `atelier` cluster directly.

```bash
dsoxlab check k8s-creer-un-cluster-kind
```

`dsoxlab clean k8s-creer-un-cluster-kind` then deletes the `atelier` cluster.
