# Challenge: Confine a Pod and detect abnormal activity, without guidance

## The situation

The security team took over the kubeadm cluster and its audit is blunt:
nothing is confined, nothing is required, nothing is watched.

- In the **`coffre`** namespace, sensitive workloads run like any container:
  free to write anywhere, to change permissions, sharing the machine's kernel.
  The Pod **`tresor`** is the protected application; **`ordinaire`** runs with
  the default runtime and must be left alone.
- The **`maille`** namespace is in an Istio mesh: **`api`** serves a page and
  **`client-maille`** calls it. From **`exterieur`**, **`client-nu`**, which
  has no sidecar, reads that page in plain text.
- In the **`donnees`** namespace, **`appli`** is the legitimate client of the
  database **`base`** (HTTP on port 80). **`intrus`** and **`annuaire`** live
  there too, and everyone talks to everyone, outside the namespace included.
- **Falco** runs on the control plane `k8s-cp.lab` and writes its alerts as
  JSON in `/var/log/falco/events.json`. Nobody would notice a shell opened in
  `tresor`.

The AppArmor and seccomp profiles you write, the sandbox runtime `runsc`
and Falco only exist on **`k8s-cp.lab`**. You work on that node, with
`kubectl` configured and root through `sudo`. No procedure is given: the
module taught you what you need. Install and uninstall nothing.

## What you must achieve

**Confine against the kernel, in `coffre`** (image `busybox:1.37`, Pods that
stay running):

1. An AppArmor profile named **`k8s-coffre-sans-tmp`** is loaded on
   `k8s-cp.lab` in **enforce** mode. It denies any write under `/tmp` and
   allows the rest.
2. A Pod **`lecteur`** runs on the node where that profile is loaded and
   declares it.
3. From `lecteur`, writing into `/tmp` is denied, reading the filesystem works.
4. A seccomp profile **`profiles/coffre-sans-chmod.json`**, in the kubelet's
   local profiles directory, refuses the `chmod` family and allows everything
   else by default.
5. A Pod **`calcul`** declares that local profile and runs.
6. In `calcul`, a `chmod` fails and creating a file works.

**Encrypt and filter the flows:**

7. The `maille` namespace only accepts mutually authenticated traffic.
8. `client-nu` no longer reaches `api`, `client-maille` still does.
9. The `donnees` namespace refuses inbound and outbound traffic by default,
   for all its Pods.
10. Only `appli` reaches `base`, on port 80.
11. Names still resolve in `donnees`, without reopening the rest of the
    outbound traffic.

**Isolate in a sandbox:**

12. The sandbox runtime known to `containerd` is offered to the cluster under
    the name **`gvisor-coffre`**.
13. A Pod **`isole`** runs in that sandbox and reads a kernel other than the
    machine's.

**Detect:**

14. A shell opened in a container of `coffre` raises an alert of a Falco rule
    named **`coffre-shell`**, with priority **`CRITICAL`**.
15. A shell opened in another namespace does not trigger that rule.
16. The rules shipped with Falco, `/etc/falco/falco_rules.yaml`, stay intact.

## How you will be graded

Sixteen requirements, equally weighted. The pass mark is **70 out of 100**, and
three requirements are **blocking**: the write into `/tmp` denied (3), the client
without a sidecar blocked while the meshed client gets through (8), and the
Falco alert for a shell in `coffre` (14). Passing the others does not make up
for missing one of them.

The tests read the node and the cluster, never your files: they really write
and run `chmod` inside the Pods, make real connections between Pods, compare
kernels, and open a shell themselves in `tresor`, then in a Pod of
`exterieur`, before reading the alerts Falco wrote.

```bash
dsoxlab check  k8s-challenge-confiner-et-detecter
dsoxlab submit k8s-challenge-confiner-et-detecter
```
