# Give each replica a stable identity with a StatefulSet

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the
namespace **`identites`** runs the **`annuaire`** as a **Deployment** with three
replicas. Its Pods have random names, change name at every recreation and keep
nothing. Yet each replica of the annuaire must be reached by a name that does
not move, and keep its own data.

The image of the annuaire:

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## What you must achieve

1. A **StatefulSet `annuaire`** with **three replicas**: the Pods
   **`annuaire-0`**, **`annuaire-1`** and **`annuaire-2`** are all **Ready**.
2. A **headless Service `annuaire`** selects these Pods, and the StatefulSet
   names it as its Service.
3. From another Pod, each stable name, **`annuaire-0.annuaire`** to
   **`annuaire-2.annuaire`**, resolves to its Pod.
4. Each replica has **its own claim**, from a template named **`donnees`**,
   **Bound** and mounted on **`/data`**.
5. The file **`/data/identite`** of replica 1 holds **`annuaire-1`** on its first
   line. Delete the Pod `annuaire-1`: the recreated Pod reads this file again,
   without it having been rewritten.
6. The **Deployment `annuaire`** has made way: only one annuaire answers.

## Useful bearings

A Deployment gives interchangeable Pods. A StatefulSet numbers its Pods from 0
to n-1, creates them in order, and gives a recreated Pod the same name and the
same volume back.

Stable names resolve only behind a Service **without a cluster address**, which
the StatefulSet names. The short name `annuaire-1` alone does not resolve: it
needs the name of the Service.

One volume per replica is not declared in the volumes of the Pod, but in a
**claim template** of the StatefulSet. The default class of the cluster creates
each volume on demand.

Write the witness file once, from the running Pod. If the container command
writes it at every start, nothing proves any more that it survived.

## How you will know it works

Each test checks one of the six states above. For stable names, the test
resolves each name from another replica and compares the address it gets with
that of the Pod. For the data, it reads the file and the events of the
StatefulSet, which say how many times the Pod `annuaire-1` was created.

```bash
dsoxlab check cka-statefulset-identite-stable
```
