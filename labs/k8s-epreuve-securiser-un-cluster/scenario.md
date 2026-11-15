# Level 5 test: secure a cluster

## The situation

You take over the kubeadm cluster that hosts the shop. It works, and that is
all anyone ever asked of it. The audit lists what it inherited:

- the API server exposes its profiler, and a CIS audit of the control plane
  fails on several counts;
- nothing records who reads what, sensitive data included;
- the shop's space, **`boutique`**, accepts any Pod and any image; its
  catalogue, **`catalogue`** (two copies, reachable at the stable name
  **`catalogue-svc`**), runs `nginxinc/nginx-unprivileged:1.21`, an image
  named by a tag, unsigned and riddled with flaws; next to it, the Pod
  **`outil-ancien`** was started "to make it work", with every privilege;
- in the invoicing space, **`facturation`**, workloads share the machine's
  kernel freely; its Pod **`export-comptable`** sends the ledger entries to the
  accountants over a channel that is already open, and nobody would notice a
  download tool starting there;
- in the **`commandes`** space, an Istio mesh accepts plain traffic: from the
  **`partenaires`** space, **`transporteur`**, without a sidecar, reads what
  the order tracking service **`suivi`** serves to the cart **`panier`**;
- in the **`paiement`** space, **`caisse`** is the legitimate client of the
  ledger **`grand-livre`**, the payments database (HTTP, port 80), and
  everyone else, the ad tracker **`publicite`** included, reaches everything,
  outside the space too.

What is on `k8s-cp.lab`, where you work with `kubectl` and root through
`sudo`:

- **Falco** runs there and writes its alerts as JSON in
  `/var/log/falco/events.json`. The sandbox runtime `runsc` is known to
  `containerd`. The AppArmor and seccomp profiles you write live there, and
  only there.
- `trivy`, `cosign` and `crane` are installed. A **local registry** answers at
  `localhost:5000`: it holds `boutique/catalogue:1.21`, a copy of the
  original image, and `boutique/outil:1.0`, another image. Neither is signed.
  The cluster itself pulls the shop's images from Docker Hub.
- The catalogue's Dockerfile is in **`/root/boutique`**. Keep your signing
  keys there too: they never leave the node.

No procedure is given, and these requirements name no Kubernetes object:
choosing them is part of the test.

## The requirements

**Control plane and audit**

1. The API server's profiler no longer answers; the API still does.
2. A new CIS audit of the control plane counts fewer failures than at the
   start, and its profiling checks pass on every component they target.
3. The API server runs with auditing on, its policy and its log living on the
   node.
4. Reads of the cluster's secrets are recorded in full; everything else as
   metadata only.

**Admission, in the `boutique` space and there only**

5. A Pod that breaks the **restricted** security standard is refused; a
   compliant one is accepted.
6. A Pod whose image is named by a tag is refused, by the cluster itself; one
   whose image is pinned by its digest is accepted. Other spaces are not
   affected.
7. `outil-ancien` no longer exists. A Pod named **`outil`** does the same work
   (it sleeps), without any of its defects, and no longer sees the host's
   processes.

**Confinement, in the `facturation` space** (image `busybox:1.37`, on `k8s-cp.lab`, for this group and the sandbox)

8. A Pod **`consultation`**, which displays invoices, can read its
   filesystem but cannot drop anything into `/dev/shm`, the refusal coming
   from an AppArmor profile loaded in enforce mode.
9. A Pod **`numerotation`**, which assigns invoice numbers, runs under a
   local seccomp profile that refuses the `chown` family and allows
   everything else.

**Network**

10. The `commandes` space requires mutual TLS: `transporteur` no longer
    reaches `suivi`, `panier` still does.
11. The `paiement` space refuses inbound and outbound traffic by default for
    all its Pods; only `caisse` reaches `grand-livre`, on port 80, and names still
    resolve.

**Sandbox, in the `facturation` space**

12. A Pod **`rendu`**, which builds invoices from received documents,
    runs in the sandbox runtime and reads a kernel other than the machine's.

**Detection**

13. A network or download tool (`wget`, `curl`, `nc` and the like) started
    in a container of `facturation` raises an alert of a Falco rule named
    **`outil-reseau-en-facturation`**, with priority **`WARNING`**; the same
    tool started in another space does not.
14. The rules shipped with Falco stay intact.

**Supply chain, and the shop**

15. The catalogue references its image by the digest the node actually runs,
    an image of `nginxinc/nginx-unprivileged` other than the original.
16. Its copy in the local registry, `localhost:5000/boutique/catalogue`, is
    signed; the public key is published in the `boutique` space, and verifying
    with it accepts that image and refuses `boutique/outil:1.0`.
17. That production image carries strictly fewer critical vulnerabilities
    than the original.
18. The Dockerfile's static analysis findings are gone, and it still builds an
    nginx image serving the shop's pages.
19. The shop still answers at `catalogue-svc`, with all its copies available,
    created under the hardening above.

## How you will be graded

Nineteen states, equally weighted, numbered P01 to P19 in the order of the
grading grid. The pass mark is **70 out of 100**, and seven states are
**critical**: the closed profiler (P01), the audit log (P04), the restricted
standard (P05), the refusal of tags (P06), mutual TLS (P10), the Falco alert
(P13) and the shop that still answers (P19). Passing the others does not make
up for missing one of them.

The tests read the node and the cluster, never your manifests: they replay the
CIS audit, read the audit log after two real requests, submit Pods to
admission, write and run `chown` inside the Pods, make real connections,
compare kernels, start `wget` themselves, verify signatures with your
published key, rescan the images and query the shop.

Hints exist, they cost points, and they go from the vaguest to the most
explicit.

```bash
dsoxlab hint   k8s-epreuve-securiser-un-cluster
dsoxlab check  k8s-epreuve-securiser-un-cluster
dsoxlab submit k8s-epreuve-securiser-un-cluster
```
