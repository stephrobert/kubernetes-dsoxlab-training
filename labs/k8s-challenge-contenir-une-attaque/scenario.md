# Detect and contain a persistence and a denial of service

## The situation

Two incidents hit the kubeadm cluster on the same morning.

In the **`reservations`** namespace, an attacker got in through a Pod named
**`diagnostic-reseau`**. The account it runs under, **`maintenance`**, reads
the Secrets of every namespace. The team removed it by hand twice: it came back
within seconds each time. Next to it runs the legitimate application
**`reservations`**, three replicas behind its Service, which the business
cannot lose.

In the **`calcul-lots`** namespace, the **`moulinette`** workload runs two
replicas with nothing to stop it from taking whatever it wants. It is bounded
here so that the node stays safe; the next one will not be. The team wants to
keep it running, but contained.

You are on the control plane, with `kubectl` configured, as root. No procedure
is given: the module taught you what you need.

## What you must achieve

1. What the attacker left to keep their access is **identified** and recorded
   in **`/root/constat-attaque.yaml`**, exported from the live object, **before
   any deletion**.
2. That object is **deleted** and the attacker's access **does not come back**,
   even once the Pod `diagnostic-reseau` is deleted: no `maintenance` account,
   no token, no right on the cluster.
3. The legitimate application **`reservations`** still has its **three
   replicas available**.
4. **`calcul-lots`** caps what is requested: at most **800m** of CPU and
   **768Mi** of memory, all Pods together.
5. A container that declares no resources in `calcul-lots` receives **default
   requests and limits**, for CPU and memory.
6. A **creation beyond that cap** is refused by the cluster.
7. While **`moulinette`** keeps running its two replicas, **`reservations`**
   keeps answering on its Service.

## How you will be graded

Seven states, equally weighted. The pass mark is **70 out of 100**, and states
**2 and 6** are **blocking**: the persistence removed for good, and a cap that
really refuses. Passing the others does not make up for missing one of them.

The tests compare the record with the object the setup created, wait for a
full cycle of the mechanism before judging that the access is gone, create
probe Pods in `calcul-lots` to see what the cluster accepts and refuses, and
send real HTTP requests to `reservations`. The feedback is limited to the first
line of each failure.

```bash
dsoxlab check  k8s-challenge-contenir-une-attaque
dsoxlab submit k8s-challenge-contenir-une-attaque
```
