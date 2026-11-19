# Challenge: Isolate an application in a namespace

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. The **`equipe-api`** and **`equipe-front`** namespaces do
not exist yet. The file **`~/namespaces/releve.txt`** is waiting for what you
will observe.

## 🎯 What you must obtain

1. The **`api`** application (an nginx Deployment, image
   `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`)
   and its **`api`** Service on port 80 are in the **`equipe-api`** namespace.
   **Nothing** is called `api` in `default`.

2. A **`client`** Pod (busybox 1.38.0, sleeping) runs in **`equipe-front`**.
   From it, `api` answers through its **name followed by the namespace**. After
   **`reponse-nom-qualifie`**, in the file: what it answers (at least the title
   line).

3. From that same Pod, the **short name** `api` fails. After **`nom-court`**,
   in the file: what you observed.

## 🧭 Useful landmarks

A namespace separates names: two objects can have the same name in two
namespaces. It does not separate the network: a Pod of any namespace can reach
a Service, if it names it properly. Without `-n`, every command targets the
default namespace of your context.

The short name of a Service is only found in the namespace of the Pod looking
for it. To target another namespace, add its name after the Service name. A
request that must fail is run with a short timeout, so as not to wait.

## ✅ How you will know it is right

The tests read the objects of both namespaces and your file, then replay both
requests from the `client` Pod.

```bash
dsoxlab check k8s-isoler-par-namespace
```
