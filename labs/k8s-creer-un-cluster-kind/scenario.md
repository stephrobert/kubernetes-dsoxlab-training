# Create a multi-node kind cluster

## The situation

The machine `k8s-kind.lab` has Docker, kind and kubectl, and you are in the
`docker` group. **To leave you the memory you need, the lab deleted the kind
clusters of the other labs** (`lab`, `boutique`, `architecture`): you broke
nothing, each lab recreates its own when you start it. The directory
**`~/atelier/`** is empty.

## What you must obtain

1. **`~/atelier/kind-atelier.yaml`** is a kind configuration file that
   describes **one control plane and two workers**.

2. A kind cluster named **`atelier`** exists, created from that file.

3. Its **three nodes are Ready**, on Kubernetes **`v1.37.0`**, on the pinned
   node image of the course:
   `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5`.

4. Its nodes have the right roles: one **control-plane** and two **workers**.

## Useful landmarks

A multi-node cluster is not described on the command line: it is described in
a file, versioned like code. The lesson gives its shape, with a `nodes` list
whose entries each carry a `role`.

The node image sets the Kubernetes version. It is not in the file: it is passed
to `kind create cluster`, with the cluster name and the path of the file.
Without a name, kind creates a cluster named `kind`.

A cluster that answers is not necessarily ready: count the nodes, read their
STATUS and VERSION columns, and wait until they are all Ready. The ROLES column
of a worker is `<none>`, which is normal.

## How you will know it is right

The tests read your file, then query the `atelier` cluster directly.

```bash
dsoxlab check k8s-creer-un-cluster-kind
```

`dsoxlab clean k8s-creer-un-cluster-kind` then deletes the `atelier` cluster.
