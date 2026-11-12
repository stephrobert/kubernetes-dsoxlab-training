# Expose an application and isolate its flows

## The situation

On the catalogue's kubeadm cluster, the **`comptoir`** team has deployed
everything in the namespace of the same name, but nothing is exposed or
protected. Two applications, **`catalogue`** and **`panier`**, each answer
behind their Service. A legacy Service, **`ancien`**, leads nowhere. The Pod
**`sonde`** resolves no name. And the database, the Pod **`base`**, accepts
everyone, including the Pod **`rodeur`** from the **`voisinage`** namespace. The
specification says what to obtain, not how.

The cluster provides a Traefik controller, reachable on port **30080** of the
node. It serves Ingresses of class **`traefik`** as well as Gateways of class
**`traefik`**. Calico enforces NetworkPolicies there.

## The specification

1. For the host **`comptoir.local`**, the path **`/catalogue`** reaches the
   `catalogue` application and the path **`/panier`** the `panier`
   application. An undeclared path, or another host, reaches neither.
2. This route is named **`vitrine`**. It is an Ingress or an HTTPRoute, your
   choice, and its controller has **taken it over**: the Ingress carries an
   address, or the HTTPRoute's Gateway is programmed and has accepted it.
3. The Service **`ancien`** has endpoints: the Pods of the `ancien`
   Deployment, reached on the port their container **really listens on**.
4. The Pod **`sonde`** resolves the name of the Service `catalogue` through the
   **cluster DNS**, and reaches it over HTTP by its short name.
5. A NetworkPolicy **`base-refus-par-defaut`** sets a **default refusal**,
   inbound and outbound, on the Pod `base` and on it alone. It allows nothing
   itself.
6. On port **5432** of the database, the Pod `backend` gets in. The Pod
   `frontend` is refused, and so is `rodeur`, although it carries the same
   label as `backend`.
7. The database **still resolves names** despite the default refusal, and
   reaches nothing else.

## How you will be graded

The challenge is graded on the **final state** of the cluster, never on the
commands typed. The **seven requirements all weigh the same**. The threshold is
**70 out of 100**, and **three requirements are blocking**: they must pass
whatever the total. They are the routed paths (requirement 1), the resolution
from `sonde` (requirement 4), and database access reserved to the backend
(requirement 6).

Four **hints** are offered, and each removes points from the scale before the
grade is computed: 2, 3, 5 then 5, 15 at most. Without hints, seven
requirements give 100, six give 86 and five give 71. With all four, seven
requirements give 85, six give 73, and five are no longer enough: 61.

No procedure is given: the lessons of the module taught everything.

```bash
dsoxlab check  k8s-challenge-exposer-et-isoler
dsoxlab submit k8s-challenge-exposer-et-isoler
```
