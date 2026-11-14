# Keep an application available during a maintenance

## The situation

The **`paiement`** application, in the **`paiement`** namespace of the kubeadm
cluster, takes the shop's payments behind its Service, also named
`paiement`. Today it runs as a **single copy**, and the next maintenance of
the worker **`k8s-w1.lab`** is planned for tonight. Nobody wants payments to
stop during it.

What the team knows about the application, on port **80**:

- `/vivant.html` answers as soon as the process runs;
- the application then takes about **twenty seconds** to warm up; until then
  `/` does not serve its page;
- `/pret.html` answers only once the warm-up is over.

The operations lead also wants the **routine report** that the morning shift
reads. It is an observation: what it reports belongs to other teams, and you
change nothing of it.

You are on the control plane, with `kubectl` configured. No procedure is given:
the module taught you what you need.

## What you must achieve

1. `paiement` runs **at least three available copies**.
2. **One** disruption budget targets the Pods of `paiement` and guarantees
   **at least two available copies** at all times, while still allowing a
   maintenance.
3. The copies are **spread across different nodes**, as many as the cluster
   can offer, by a rule declared in the application's description.
4. **Readiness and liveness probes** are declared, and a copy **receives
   traffic only once it is ready**: never while it is warming up.
5. **While a node is evacuated**, `paiement` keeps **at least two available
   copies**, and the evacuation completes.
6. The file **`~/routine/rapport.txt`** reports, as the cluster really is:
   - the **nodes**, each by its name;
   - the **Pods in error**, each by its name or the name of what manages it;
   - the **orphan resources**: the finished Jobs still kept;
   - the **expiry date** of the control plane certificates, as `kubeadm` or
     `openssl` show it, or written as `YYYY-MM-DD`.

## How you will be graded

Six states, equally weighted. The pass mark is **70 out of 100**, and states
**2 and 5** are **blocking**: the budget that guarantees the minimum, and the
minimum kept during the evacuation. Passing the others does not make up for
missing one of them.

Each check **acts on the cluster**, and says so here: it evicts one copy of
`paiement` and watches whether its replacement gets traffic before it is
ready; then it **evacuates `k8s-w1.lab` itself**, measures the available copies
during the evacuation, puts the node back into service and spreads the copies
again. The report is compared with the state of the cluster at the time of the
check. The feedback is limited to the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-garantir-la-disponibilite
dsoxlab submit k8s-challenge-garantir-la-disponibilite
```
