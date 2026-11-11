# Isolate an application in a namespace

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. The namespaces **`equipe-api`** and **`equipe-front`** do not exist
yet. The record **`~/namespaces/releve.txt`** waits for what you observe.

## What you must obtain

1. The application **`api`** (an nginx Deployment on
   `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`)
   and its Service **`api`** on port 80 are in the **`equipe-api`** namespace,
   and **nothing** is named `api` in `default`.

2. A Pod **`client`** (busybox 1.38.0, sleeping) runs in **`equipe-front`**.
   From it, `api` answers through its **namespace-qualified name**, and
   **`reponse-nom-qualifie`** holds what it answers (at least the title line).

3. From that same Pod, the **short name** `api` fails, and **`nom-court`** says
   what you observed.

## Useful landmarks

A namespace separates names: two objects can carry the same name in two
namespaces. It does not separate the network: a Pod from any namespace can reach
a Service, as long as it names it properly. Without `-n`, each command targets
the default namespace of your context.

The Services lesson showed it: the short name of a Service only resolves in the
namespace of the client. To target another namespace, add its name after the
Service name. A request that is not supposed to succeed is started with a short
timeout, so as not to wait.

## How you will know it is right

The tests read the objects of both namespaces and your record, then replay both
requests from the client Pod.

```bash
dsoxlab check k8s-isoler-par-namespace
```
