# Level 2 test: deploy an application that keeps its data

## The situation

The shop hands you its complete deployment, on the kind cluster **`multi`**
that your `kubectl` already targets: one control plane and two workers.
Everything lives in the **`magasin`** space, empty for now. The directory
**`~/boutique/`** is empty too. The requirements say what to obtain, not how:
it is up to you to choose the resources.

The images:

```text
storefront   : nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
everything else : busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The requirements

**The storefront**

- It runs **three interchangeable copies**, on the storefront image **referred
  to by digest**. In the cluster, it is named **exactly `vitrine`**, with no
  prefix or suffix, even when shipped by the overlay.
- Its description lives in a Kustomize **base**, **`~/boutique/base/`**, and it
  is shipped by an **overlay** **`~/boutique/overlays/prod/`** built on that
  base. The cluster matches this overlay exactly.
- **Every container** of the storefront, preparation step and companion
  included, declares what it requests and its limit. The server is probed at **startup**, for **liveness** and for
  **readiness**, on its **port 80**.
- A **preparation step** writes the home page and finishes before the server
  starts. A **companion** repeats in its logs, line by line, the accesses the
  server writes in `/var/log/nginx/access.log`, through a shared volume. The
  companion is **ready before the server** and stays active next to it for the
  whole life of the Pod, so that no line is lost.
- **No Pod** of the `magasin` space restarts.

**The database `catalogue`**

- It runs **two replicas** with a **stable identity**, created in order and
  named **`catalogue-0`** and **`catalogue-1`**, all **Ready**.
- Each replica has **its own volume**, mounted on **`/data`**. The grader will
  write data there on `catalogue-0`, delete that Pod, and read the data again on
  the recreated Pod.
- These volumes are **created on demand** by a storage class that **keeps** them
  when their claim goes away.

**The backup**

- The scheduled task is named **exactly `sauvegarde`**.
- It runs **every day at 2:30** and writes a file whose name starts with
  **`sauvegarde`** at the root of a persistent volume claimed under the name
  **`archives`**.
- Start it **once by hand** from its schedule, and let that run finish.

**The agent `collecteur`**

- It is named **exactly `collecteur`** in the cluster.
- It runs **one Ready copy on each node**, control plane included, and the
  control plane **keeps its taint**.

**The custom resource**

- The **`Sauvegarde`** CRD of the lesson is already installed. Create in
  `magasin` the Sauvegarde **`nocturne`**, with source **`catalogue`**, kept
  **14 days**, nothing more. The API must still refuse a retention outside the
  bounds of the schema.

## How you are graded

The test is graded on the **final state of the cluster**, on `~/boutique/` and
on the volumes, never on the commands typed. It has **ten criteria**, P01 to
P10, which all weigh the same. The threshold is **70 out of 100**, and **five
criteria are critical**: they must all pass, whatever the total. They are the
delivery from Kustomize with no difference (P01), the storefront available on
its digest without restart (P02), the database with a stable identity and one
volume per replica (P05), the grader's data that survives its Pod (P06), and the
volumes created by the class and kept (P07).

You can run `dsoxlab check` as often as you like, but each check acts on the
cluster: it writes data in `catalogue-0`, deletes that Pod and waits for it to
come back, and sends one request to the storefront.

Seven criteria give 70, the five critical ones among them. No procedure is
given, and the test offers **no hint**: the lessons of level 2 taught
everything.

```bash
dsoxlab check  k8s-epreuve-deployer-une-application
dsoxlab submit k8s-epreuve-deployer-une-application
```
