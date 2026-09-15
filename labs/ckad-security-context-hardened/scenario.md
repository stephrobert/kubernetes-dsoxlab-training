# Harden a Pod with a securityContext

## The situation

The security team has set the rule for everything running in the **`lab`**
namespace: no root, no privilege escalation, a read-only root filesystem,
and no Linux capability. The application to deliver is a web server, image
**`nginxinc/nginx-unprivileged:1.27-alpine`**, which listens on port
**8080**.

That server needs to write somewhere in order to start. With a read-only
root filesystem it no longer can, and it will say so in its logs. It is up
to you to give it exactly the writable spaces it needs, and nothing more.

## What you must achieve

1. A Pod **`hardened`** in `lab`, with that image, **`Running`**.

2. The Pod runs as user **1000**, and refuses to run as root. The container
   allows **no privilege escalation**, its root filesystem is
   **read-only**, and it drops **all** the capabilities.

3. The server **answers** over HTTP on its port 8080.

4. From the inside: the process really is user 1000, a write at the root is
   denied, and the application really has its writable spaces.

## Useful bearings

The `securityContext` exists at two levels, and not every field is accepted
at both. What concerns the user is declared at the Pod level or at the
container level; what concerns the filesystem, escalation and capabilities
is declared at the container level.

An `emptyDir` volume is a writable space that is born and dies with the Pod.
It mounts wherever you want, including on top of a directory of the image.

## How you will know it works

The tests read the Pod definition, enter the container to check the user and
attempt a write, and query the server from the node.

```bash
dsoxlab check ckad-security-context-hardened
```
