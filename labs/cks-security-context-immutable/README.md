# Make a container immutable without bringing it down

**CKS** lab, *Minimize Microservice Vulnerabilities* domain (20 % of the
exam), the immutable container.

Distinct from [`cks-secure-existing-pod`](../cks-secure-existing-pod/), which
covers privilege, host namespace sharing and process identity. This one covers
the **filesystem**, and the real cost of that constraint: an application that
writes during startup does not come back up.

**The proof path was measured, not assumed**, and that is the delicate point
of the lab. The image already runs under UID 101: the root is refused to it by
POSIX permissions before any hardening. A test doing `touch /preuve` would
therefore be **green before the work**.

Measured on 2026-09-16, on a bare Pod then a hardened one:

| path | bare Pod | hardened Pod |
|---|---|---|
| `/preuve` | Permission denied | Read-only file system |
| `/usr/share/nginx/html` | Permission denied | Read-only file system |
| `/var/log/nginx` | Permission denied | Read-only file system |
| **`/etc/nginx/conf.d`** | **WRITABLE** | Read-only file system |

Only the last one distinguishes the two states: the image opens it to its own
UID so its entrypoint scripts can write there, and only
`readOnlyRootFilesystem` closes it.

The other measurement that makes the lab: with no ephemeral volumes, nginx
stops on `mkdir() "/tmp/proxy_temp" failed (30: Read-only file system)`. The
candidate must read that log rather than guess, which the scenario says
without handing over the paths.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Pod Security Standards](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |

```bash
dsoxlab run   cks-security-context-immutable
dsoxlab check cks-security-context-immutable
```
