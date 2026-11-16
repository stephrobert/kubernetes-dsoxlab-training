# Make Falco raise an alert on a shell opened in a protected namespace

## The situation

**Falco** runs on the control plane `k8s-cp.lab`, installed from the official
package with the modern eBPF probe. It only has its **shipped rules**, in
`/etc/falco/falco_rules.yaml`, and writes its alerts as JSON, one per line, to
**`/var/log/falco/events.json`**. It also loads any rules file placed in
**`/etc/falco/rules.d/`**, when the service `falco-modern-bpf.service` starts.

In the namespace **`paiements`**, the Pod **`caisse`** processes payments. The
security team wants to know **at once** if someone opens a shell in it. The
namespace **`accueil`** holds the Pod **`vitrine`**, which is not concerned: a
shell there is an ordinary gesture. Both Pods run on `k8s-cp.lab`, where Falco
watches.

You are on the control plane, with `kubectl` configured, and `sudo`.

## What you must achieve

1. A Falco rule named exactly **`Shell dans paiements`**, with priority
   **`CRITICAL`**, that fires as soon as a **shell starts** in a container of the
   namespace `paiements`.
2. A shell opened in a container of **another** namespace does **not** fire
   this rule.
3. The **shipped rules** stay untouched: your rule lives in its own file.

## Landmarks

A Falco rule fits in a few keys: `rule`, `desc`, `condition`, `output` and
`priority`. The condition combines **macros** shipped with Falco (a process
that starts, a container, a process of the shell family) with **fields** such
as the Kubernetes namespace of the event.

The shipped rules file is replaced at each update: you do not write in it. A
badly written rule prevents Falco from starting, and the service log says why.
After placing a file, Falco must be restarted to read it.

Beware of the shipped rule `Terminal shell in container`: it only fires for a
shell **with a terminal**. The request targets any shell that starts, with or
without a terminal.

## How you will know it works

The tests open a shell in `caisse`, then in `vitrine`, and read what Falco
wrote to its log. They also compare the shipped rules file to the fingerprint
the package keeps of it.

```bash
dsoxlab check cks-falco-detecter-un-shell
```
