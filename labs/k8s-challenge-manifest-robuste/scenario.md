# Ship a robust manifest from a set of requirements

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the shipping
team hands you its **`colis`** application, a web server, to ship into the
**`expedition`** namespace in two variants, **dev** and **prod**. At the same
time, the **`etiquettes`** Pod of that namespace no longer starts. The
**`~/expedition/`** directory is empty. The requirements say what to obtain, not
how.

The images:

```text
application: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
tooling    : busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The requirements

1. **One single Kustomize base**, in `~/expedition/base/`, and two overlays,
   `~/expedition/overlays/dev/` and `~/expedition/overlays/prod/`. They differ
   only by the **number of replicas** (1 in dev, 3 in prod), the **name prefix**
   (`dev-`, `prod-`) and the **`env`** label (`dev`, `prod`). Both variants live
   in `expedition`: the prod Deployment is therefore named **`prod-colis`**.
2. **`prod-colis`** has its **3 replicas available**, on the application image
   **referred to by digest**.
3. Each Pod of the application carries an **init container** that prepares the
   home page and completes before the server starts, and a **native sidecar**
   whose logs repeat, line by line, the accesses the server writes on a **shared
   volume** (the server writes its accesses to `/var/log/nginx/access.log`).
4. **Every container** declares its requests and limits; the server's **memory
   limit** is **`128Mi`**.
5. The **startup**, **liveness** and **readiness** probes query the server over
   HTTP on its **port 80**, and every Pod is **Ready without restart**.
6. A CronJob **`purge-colis`** runs **every day at 3:00**, keeps **two**
   successful Jobs and **one** failed, and **never runs two purges at once**.
7. A Job **`inventaire`** is **complete** with **three completions**.
8. **The cluster matches the folder**: comparing each overlay with the cluster
   finds no difference.
9. **Before any repair**, write in **`~/expedition/cause.txt`** why
   **`etiquettes`** does not start: what it looks for without finding it, by its
   name, and that it is missing. Then leave the file untouched.
10. **`etiquettes`** runs again, **without having been recreated**. It expects the
    value **`FORMAT=A6`**.

## How you will be graded

The challenge is graded on the **final state** of the cluster and of your files,
never on the commands typed. The **ten requirements all weigh the same**. The pass
mark is **70 out of 100**, and **three requirements are blocking**: they must
succeed whatever the total. They are `prod-colis` available on its digest
(requirement 2), the probes with Pods Ready without restart (requirement 5), and
the cause recorded before the repair (requirement 9).

Four **hints** are offered, and each one takes points off the scale before the
score is computed: 2, 3, 5 then 5, so 15 at most. With all four, ten requirements
met give 85, nine give 76, and eight give 68, below the pass mark. Without a hint,
seven requirements are just enough (70); with the first hint, they give only 69.

No procedure is given: the lessons of the module taught everything.

```bash
dsoxlab check  k8s-challenge-manifest-robuste
dsoxlab submit k8s-challenge-manifest-robuste
```
