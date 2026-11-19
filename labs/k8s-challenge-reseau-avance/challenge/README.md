# Challenge: Repair, open, route out and audit the flows of a Cilium cluster, without guidance

## The situation

You take over the Cilium cluster of the `net-*` hosts: a control plane,
`net-cp.lab`, and two workers, `net-w1.lab` and `net-w2.lab`. It runs
**without kube-proxy**: Cilium 1.20.5 replaces it. Hubble is on, and the Cilium
**egress gateway** is already enabled. Cilium 1.20.5 declares Kubernetes 1.33
to 1.36, and this cluster runs 1.37.

The previous team leaves four open issues:

- In the namespace **`catalogue`**, the Service **`catalogue`** no longer
  answers from the Pod **`client`**. The Pods of the Deployment `catalogue` do
  run, though. Someone suggests reinstalling kube-proxy.
- The namespace **`commandes`** refuses all inbound traffic, through the
  NetworkPolicy **`refus-par-defaut`**. The Pod **`panier`** of the namespace
  **`boutique`** must now reach the Service **`stock`** on port 80. The Pod
  **`robot`**, in the same namespace, must not.
- The network team accepts traffic from the namespace **`facturation`** to its
  witness server only if it comes from the address of **`net-w2.lab`**. The
  witness URL is in the ConfigMap **`temoin`** of `facturation`. The witness
  logs every request, with the source address it sees.
- In the namespace **`paiement`**, three clients call the **`api`** every two
  seconds. One of them complains: the API no longer answers it. Nobody knows
  which one, or why.

You work on `net-cp.lab`, with `kubectl` and `helm` configured and root through
`sudo`. No procedure is given: the module taught you what you need. Install or
uninstall nothing.

## What you must achieve

1. The Service `catalogue` answers again from the Pod `client`, with the page
   the Pods of the Deployment `catalogue` serve. kube-proxy stays absent, and
   Cilium still replaces it.
2. `panier` reaches `stock` on port 80. `robot`, and any Pod of another
   namespace, stay refused.
3. The traffic of the namespace `facturation` to the witness leaves through
   **`net-w2.lab`**: the witness log records the address of that node. This
   holds for any Pod of the namespace, including a Pod created after your
   change. The other namespaces still leave through their own node.
4. A ConfigMap **`flux-refuse`**, in `paiement`, names the refused flow with
   three keys: **`source`** (the client Pod), **`destination`** (the called
   Pod) and **`port`** (the destination port). The flow must **stay refused**:
   you name it, you do not open it.

## How you will be graded

Four states, equally weighted. The pass mark is **70 out of 100**: three states
out of four. The feedback is limited to the list of unmet criteria, by their
label, and the score: no message says why.

The tests read the cluster, never your files. They query the Service from
`client`, make real connections from `panier`, `robot` and a Pod of another
namespace, create a new Pod in `facturation` themselves and read the witness
log, then compare your ConfigMap with the flows Hubble marks `DROPPED` in the
last two minutes.

```bash
dsoxlab check  k8s-challenge-reseau-avance
dsoxlab submit k8s-challenge-reseau-avance
```
