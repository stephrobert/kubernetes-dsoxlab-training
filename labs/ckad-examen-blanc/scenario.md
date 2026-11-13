# CKAD mock exam: 17 tasks in 120 minutes

## Before you start

This exam follows the CKAD format: hands-on tasks, graded on the final state of
the cluster, with no hint. **Plan for 120 minutes**, in one sitting, and start
your own timer: the tool does not. The tasks are independent.

You start from the **base**, `k8s-cp.lab`, the session `dsoxlab run` opens.
**Each task names the host to do it on**: connect with `ssh`, work, then go
back to the base with `exit` before the next task. Never run `ssh` from a task
host. Both hosts, **`k8s-cp.lab`** and **`k8s-w1.lab`**, have `kubectl`
configured, the `k` alias and completion. **No context sets the namespace**:
each task gives its own, write it in your commands. A resource created in the
wrong namespace does not count.

The images to use:

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The tasks

### Task 1 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

Create the CronJob **`purge`** (busybox image, command `echo purge`), which runs
**every ten minutes**, keeps **two** successful runs in its history and **never
runs two at once**.

Then go back to the base: `exit`.

### Task 2 (10%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

Create the Pod **`journal`**. Its **`app`** container (busybox) appends a
timestamped line to the file **`/var/log/app/app.log`** every two seconds. A
sidecar container **`lecteur`** (busybox) shares that directory through an
`emptyDir` volume and prints the file continuously on its standard output.

Then go back to the base: `exit`.

### Task 3 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

Create the claim **`cache`** of **50Mi**, on the class `local-path`, and the Pod
**`stockage`** (busybox) which mounts it on **`/cache`** and writes the file
**`/cache/ok`** there, whose content is `ok`.

Then go back to the base: `exit`.

### Task 4 (10%)

**Connect: `ssh k8s-w1.lab`** · namespace **`boutique`**

The storefront is served in its blue version (Deployment `vitrine-bleu`). Switch
it to the green version: the Deployment **`vitrine-vert`** runs **three replicas
on nginx 1.30.6**, and the Service **`vitrine`** sends to them only. Keep
`vitrine-bleu` in place for a rollback.

Then go back to the base: `exit`.

### Task 5 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`boutique`**

Update the Deployment **`catalogue`** to **nginx 1.30.6**, with a strategy that
adds **only one Pod at a time** and removes **none** before the new one is ready.

Then go back to the base: `exit`.

### Task 6 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`boutique`**

Complete the overlay **`~/examen/kustomize/overlays/boutique/`** so that it
places the application in the **`boutique`** namespace, with **2 replicas** and
the **nginx 1.30.6** image, then apply it.

Then go back to the base: `exit`.

### Task 7 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

Add to the Deployment **`api`** an HTTP **readiness** probe on `/`, port 80, and
a TCP **liveness** probe on port 80. Its two Pods must stay ready.

Then go back to the base: `exit`.

### Task 8 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

The manifest **`~/examen/pdb-ancien.yaml`** uses an API removed from Kubernetes.
Rewrite it in its current version, without changing what it describes, and
apply it.

Then go back to the base: `exit`.

### Task 9 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

The Pod **`outil`** does not start. Make it run on the busybox image given above.

Then go back to the base: `exit`.

### Task 10 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

Create the ConfigMap **`parametres`** (key `app.conf`, content `niveau=debug`)
and the Pod **`lecture-config`** (busybox) which receives it as a **file**,
**`/etc/app/app.conf`**.

Then go back to the base: `exit`.

### Task 11 (5%)

**Connect: `ssh k8s-cp.lab`** · namespace **`atelier`**

Create the Secret **`jeton`** (key `valeur`, value `jeton-de-demonstration`) and
the Pod **`lecture-secret`** (busybox) which receives it in the variable
**`JETON`**.

Then go back to the base: `exit`.

### Task 12 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`securite`**

Create the Pod **`durci`** (busybox, `sleep infinity`) which runs **as uid
1000**, refuses to run as root, has a **read-only** root filesystem, cannot
**escalate its privileges** and has dropped **all** its capabilities.

Then go back to the base: `exit`.

### Task 13 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`securite`**

Set the quota **`plafond`**: 5 Pods at most, 2 CPU and 1Gi of memory in limits.
Then create the Pod **`mesure`** (busybox, `sleep infinity`) which requests 100m
of CPU and 64Mi of memory, limited to 200m and 128Mi, and fits in that quota.

Then go back to the base: `exit`.

### Task 14 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`securite`**

Create the ServiceAccount **`deployeur`** and the Pod **`outil-sa`** (busybox,
`sleep infinity`) which runs under that account, **without** the account's token
being mounted in the Pod.

Then go back to the base: `exit`.

### Task 15 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`boutique`**

Only the Pod **`front`** may reach the Pod **`interne`** (port 5678). The Pod
`autre` is refused.

Then go back to the base: `exit`.

### Task 16 (10%)

**Connect: `ssh k8s-w1.lab`** · namespace **`boutique`**

The Service **`stock`** leads to no Pod. Repair it, without touching the
Deployment `stock`, so that the Pod `front` gets the answer `stock` when it
queries `http://stock/`.

Then go back to the base: `exit`.

### Task 17 (5%)

**Connect: `ssh k8s-w1.lab`** · namespace **`boutique`**

Create the Ingress **`infos`**, of class `traefik`, which sends
`http://infos.examen/infos` to the Service **`infos`**. The controller answers on
the node's port **30080**.

Then go back to the base: `exit`.

## How you will be graded

Twenty states, 5 points each; the 10% tasks carry two. The weights follow those
of the domains of the official CKAD curriculum. The threshold is **66 out of
100**, as in the real exam: 14 states out of 20 are needed. No hint is offered,
and the feedback is the verdict only, as on exam night.

## What this mock exam does not reproduce

- **One cluster per task**: the real exam chains several. Here, both hosts
  point at the same cluster, with different namespaces.
- **The remote desktop and its browser** limited to the official documentation.
- **The timer**, which you keep yourself.
- **Partial credit** inside a state: a state is passed or not.
- **Helm and image building**, which the curriculum cites and the course teaches
  elsewhere.

```bash
dsoxlab check  ckad-examen-blanc
dsoxlab submit ckad-examen-blanc
```
