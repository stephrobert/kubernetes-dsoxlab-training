# Place Pods, cap a namespace and scale, without guidance

## The situation

On the kind cluster **`capacite`** that your `kubectl` already targets (one
control plane, three workers), the **`atelier`** namespace runs four
applications, deployed without any placement rule or resource:

- **`rendu`**, the render engine, which must have a node to itself;
- **`accueil`**, the ordinary front page, which must follow its load;
- **`stockage`**, which needs a fast disk;
- **`galerie`**, two replicas that must survive the loss of a node.

The namespace has no ceiling and gives its containers no default value. A
metrics-server answers: `kubectl top pods` works.

No procedure is given: the module taught you what you need.

## What you must achieve

1. The node **`capacite-worker3`** is reserved: it carries the taint
   **`dedie=calcul:NoSchedule`** and the label **`dedie=calcul`**.
2. **`rendu`** runs on `capacite-worker3`, because it **tolerates** the taint
   **and** **selects** that node. **`accueil`** runs **elsewhere**.
3. **`stockage`** asks for a **required** node affinity on **`disque=ssd`** and
   a **preferred** one, of weight **50**, for the zone **`zone-b`**
   (`topology.kubernetes.io/zone`). The node **`capacite-worker2`** carries the
   label **`disque=ssd`**, and `stockage` runs on it.
4. The replicas of **`galerie`** run on **different nodes**, and its
   description guarantees it.
5. A **ResourceQuota** caps `atelier` at **2 CPU** and **2Gi** of requests,
   **4 CPU** and **4Gi** of limits, and **15 Pods**. A Pod that asks for more
   is refused, which a server-side dry run shows.
6. A **LimitRange** gives every container that declares nothing a request of
   **100m** CPU and **128Mi**, and a limit of **200m** CPU and **256Mi**: a Pod
   without requests is accepted, and comes back completed.
7. An **HPA** scales **`accueil`** between **2** and **5** replicas, at
   **50 %** average CPU utilization, and it **reads a value**: its target is
   not `<unknown>`.
8. **Under load**, the HPA takes `accueil` **beyond its minimum**.

## How you will be graded

Eight states, equally weighted. The pass mark is **70 out of 100**, and states
**2 and 5** are **blocking**: the reserved application on its node, and the
ceiling of the namespace. Passing the others does not make up for missing one
of them.

The tests read where the Pods really run and what their descriptions ask, and
submit test Pods in server-side dry run, which creates nothing. For state 8,
**the test generates the load itself**: it runs a CPU loop inside every Pod of
`accueil` for about two minutes, and waits up to two minutes for the
Deployment to grow. You have nothing to start for it, and a check can last
that long.

Four **hints** are offered, and each removes points from the scale before the
grade is computed: 2, 3, 5 then 5. The feedback is limited to the verdict:
passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-placer-et-plafonner
dsoxlab submit k8s-challenge-placer-et-plafonner
```
