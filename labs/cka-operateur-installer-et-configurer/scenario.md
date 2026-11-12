# Install an operator and configure what it runs

## The situation

The registry team wants a MongoDB database on the catalogue's kubeadm cluster,
and it does not want to operate it by hand: an **operator** will do it. The
chosen operator is **MongoDB Controllers for Kubernetes (MCK) 1.15.0**, whose
official compatibility matrix covers Kubernetes 1.35, 1.36 and 1.37.

The cluster provides a default StorageClass, `local-path`. Nothing else is
installed: neither the operator, nor its definitions, nor its namespace.

The operator's two manifests, at the version tag:

```text
https://raw.githubusercontent.com/mongodb/mongodb-kubernetes/1.15.0/public/crds.yaml
https://raw.githubusercontent.com/mongodb/mongodb-kubernetes/1.15.0/public/mongodb-kubernetes.yaml
```

The two images to pin, with their digest:

```text
quay.io/mongodb/mongodb-kubernetes:1.15.0@sha256:953d43a57a5d4ebcb7f726a6d93dead23c75231ca753b68865bf098232cbce1a
quay.io/mongodb/mongodb-community-server:9.0.8-ubi8@sha256:77351e6c8e806a5f55949212e2fe521d0866069d3348d1032414e2e256cd9651
```

## What you must achieve

1. The CRD **`mongodbcommunity.mongodbcommunity.mongodb.com`** is
   **Established**.

2. The Deployment **`mongodb-kubernetes-operator`**, in the **`mongodb`**
   namespace, is **available**, and runs the operator image **pinned by its
   digest**.

3. A **MongoDBCommunity** resource named **`registre`**, in `mongodb`, in phase
   **`Running`**. It is a **one-member** replica set, version **`9.0.8`**, with
   a user **`atelier`** (database `admin`) whose password lives in the Secret
   **`atelier-mot-de-passe`**, key `password`.

4. The StatefulSet **`registre`** and the Service **`registre-svc`** exist, and
   they **belong to the resource** `registre`: the operator created them.

5. The **`mongod`** container runs on the server image **pinned by its
   digest**.

6. **By editing only the resource**, you have set mongod's slow operation
   threshold to **250 ms** (`operationProfiling.slowOpThresholdMs`), and mongod
   has **restarted with that setting**.

## Useful bearings

Order matters: the namespace first, since the operator's manifest assumes it
without creating it; the definitions next; the operator last. A resource
applied before its CRD is refused.

The operator's manifest names its images by **tag**. Replace the operator's with
its pinned form **before** applying it. The MongoDB server does not appear in
that manifest: the operator builds its name from the resource's version. It is
therefore pinned **in the resource**, under `spec.statefulSet`, on the `mongod`
container.

This cluster's nodes are small. The replica set's default requests do not fit:
reduce them under `spec.statefulSet`, to **100m** of CPU per container (`mongod`
and `mongodb-agent`), as one of the samples in the operator's repository does
(`public/samples`).

The first move to `Running` takes several minutes: the server image weighs
433 MB. Once the resource is edited, the operator goes back through `Pending`
while it restarts mongod, then returns to `Running`.

## How you will know it works

Each test checks one of the six states above. The fourth reads the objects'
owners: a StatefulSet built by hand would carry the same names, without an
owner. The sixth reads mongod's **startup options**: a setting changed live in
mongod does not alter them, and would disappear at the first restart.

```bash
dsoxlab check cka-operateur-installer-et-configurer
```
