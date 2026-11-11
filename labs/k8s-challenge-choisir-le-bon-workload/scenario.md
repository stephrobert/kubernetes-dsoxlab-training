# Choose and deploy the right workload for three needs

## The situation

On the kind cluster **`multi`**, which your `kubectl` already targets, the
shop's warehouse has three needs to serve in the namespace **`entrepot`**, empty
for now. The cluster has one control plane and two workers. The requirements
describe each need; it is up to you to choose the type of object that serves it.
The directory **`~/entrepot/`** holds the definition of a custom resource,
**`collecte-crd.yaml`**, that nobody has installed yet.

The image to use for the database and for the agent:

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The requirements

1. **The database `inventaire`** runs **three replicas** with a **stable
   identity**, created in order and named **`inventaire-0`**, **`inventaire-1`**
   and **`inventaire-2`**, all **Ready**.
2. Each replica is reached by a **stable name** of the form
   **`inventaire-N.<service>`**, served by a Service **without a cluster
   address**.
3. Each replica has **its own volume**, mounted on **`/data`**. The file
   **`/data/marque`** of replica 1 holds **`inventaire-1`** on its first line.
   Delete the Pod `inventaire-1`: the recreated Pod reads this file again
   **intact**.
4. **The agent `collecteur`** runs **one copy on each node**, and each copy is
   **Ready**.
5. The control plane node **keeps its taint**: the agent runs there because it
   **tolerates** it, not because the taint was removed.
6. The custom resource **`Collecte`** is installed and **Established**. The
   Collecte **`journaux`**, in `entrepot`, targets **`/var/log`**, collects
   every **60 seconds** and keeps **30 days**, nothing more.
7. The API **refuses** any Collecte kept **more than 90 days**. The file
   provided does not enforce it yet.

## How you are graded

The challenge is graded on the **final state** of the cluster, never on the
commands typed. The **seven requirements all weigh the same**. The threshold is
**70 out of 100**, and **three requirements are blocking**: they must pass
whatever the total. They are the data of replica 1 read again intact
(requirement 3), the taint of the control plane kept and tolerated
(requirement 5), and the Collecte `journaux` matching, with its resource
Established (requirement 6).

Four **hints** are offered, and each one takes points off the scale before the
grade is computed: 2, 3, 5 then 5, 15 at most. Without a hint, seven
requirements give 100, six give 86 and five give 71. With the first hint, five
requirements still give 70; with the first two, they give only 68, below the
threshold. With all four, at least six requirements are needed (73).

No procedure is given: the lessons of the module taught everything.

```bash
dsoxlab check  k8s-challenge-choisir-le-bon-workload
dsoxlab submit k8s-challenge-choisir-le-bon-workload
```
