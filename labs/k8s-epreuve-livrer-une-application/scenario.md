# Level 3 test: expose, configure and ship an application

## The situation

A music festival hands you its platform, on the kind cluster **`capacite`**
that your `kubectl` already targets: one control plane and three workers. The
previous team left in a hurry. The requirements say what to obtain, not how:
it is up to you to choose the resources, and to find what is broken.

What you inherit:

- the **`festival`** space holds the ticket office **`billets`** (the frontend,
  two copies), the application **`programme`**, the database **`registre`**,
  and a poster generator **`affiches`**. Several of them do not run, or not as
  they should;
- the **`paiement`** space holds the payment component **`caisse`**, which no
  longer answers at **`http://caisse.paiement`**, although its copies run;
- the **`partenaires`** space holds **`partenaire`**, the client of a partner;
- the node **`capacite-worker3`** is reserved for the database: the platform
  team has fenced it off and labelled it **`reserve=registre`**.

The cluster's HTTP entry point, Traefik, answers on port **30080** of every
node, at the node's address. It serves the cluster's standard HTTP routes.

## The requirements

1. **Exposure.** From outside the cluster, for the host **`festival.local`**,
   the path **`/billets`** reaches the ticket office and the path
   **`/programme`** reaches the programme. An undeclared path, or another host,
   reaches neither.
2. **The failing component.** Before any repair, write in
   **`~/epreuve/cause-caisse.txt`** why `caisse` does not answer: name what
   prevents it, and how. Then repair it, without touching the file again: its
   date is compared with that of your repair. `caisse` answers again at
   `http://caisse.paiement` from any Pod of the cluster.
3. **Name resolution.** From `partenaire`, the full name
   **`programme.festival.svc.cluster.local`** resolves, and the programme
   answers there over HTTP, on port **80**.
4. **Isolation.** On port **5432** of the database, only the ticket office
   gets in. The programme is refused, and so is any client of another space.
5. **The database's outbound traffic.** The database still resolves names,
   and every other outbound flow is refused to it.
6. **Placement.** The database runs on the reserved node, and nothing else of
   `festival` runs there. The two copies of the ticket office never share a
   node: their description guarantees it, it is not left to chance.
7. **The ceiling.** `festival` as a whole may never reserve more than
   **2 CPU** and **2 GiB** of memory, never exceed **4 CPU** and **4 GiB** in
   limits, nor hold more than **15 Pods**. A workload that would exceed it is
   refused at creation.
8. **Default values.** A container of `festival` that declares nothing
   receives a request of **100m** CPU and **128Mi** of memory, and a limit of
   **250m** CPU and **256Mi**. The `affiches` workload runs.
9. **Scaling.** The programme follows its processor load between **2** and
   **6** copies, aiming at **60 %** of the CPU each copy reserves, and its
   scaling actually reads a value.
10. **Identity.** The programme runs under an identity of its own, used by no
    other workload. It never calls the API: no credential is given to its
    containers. That identity may **read the ConfigMaps of `festival`**, and
    nothing else, anywhere: no other right in the space, none elsewhere, none
    on the cluster.
11. **Hardening.** The programme's container runs **without root**, under a
    numeric user, with a **read-only root filesystem** and **no capability**,
    and the programme still answers.

## How you will be graded

The test is graded on the **final state of the cluster** and on the cause
file, never on the commands typed. It has **eleven criteria**, one per
requirement, all of equal weight. The pass mark is **70 out of 100**, so at
least eight criteria, and **six criteria are critical**: they must all pass,
whatever the total. They are the exposure (1), the repaired component with its
cause recorded first (2), the isolation of the database (4), the ceiling (7),
the identity (10) and the hardening (11).

Each check acts on the cluster: it runs commands inside `partenaire` and inside
copies of your applications, and submits test workloads to `festival` in
server-side dry run, which creates nothing.

No procedure is given, and the test offers **no hint**: the lessons of
level 3 have taught everything. Count about two hours.

```bash
dsoxlab check  k8s-epreuve-livrer-une-application
dsoxlab submit k8s-epreuve-livrer-une-application
```
