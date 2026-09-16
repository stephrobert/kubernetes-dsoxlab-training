# Make a container immutable without bringing it down

## The situation

In the **`catalogue`** namespace, the **`vitrine`** Deployment serves a page
in two replicas. It already runs as an unprivileged user, which the team
considered sufficient.

It is not. From inside the container, the image opens paths to its own user
that can be written to, its configuration included. An attacker who gets code
execution in that container can drop whatever they want there, and what they
drop outlives their visit.

A **`client`** Pod is there to query the service from within the cluster.

## What you must achieve

1. The container's filesystem can no longer be written to.

2. The container can no longer gain extra privileges, and it keeps **no**
   kernel capability.

3. The process does not run as the administrator, and the cluster knows it.

4. **The site still answers.** That is the hard half: an application that
   writes during startup does not come back up in a closed filesystem.

Modify what exists. Do not replace the Deployment with an object under another
name.

## Useful bearings

Closing the filesystem closes **everything** the image carries. What must stay
writable is reopened path by path.

Do not guess which paths: the application says so. When a Pod fails to come
back up, its log names the first file it tripped on.

The reopened paths need not survive a container restart: they hold cache and
temporary files. The volume type that fits is the one whose content is lost
with the Pod.

Not all fields live at the same level: what concerns process identity is
accepted at both Pod and container level, while escalation, capabilities and
the filesystem are accepted only at container level.

An existing Pod does not change `securityContext`. The Deployment is what you
modify, and its Pods are recreated.

## How you will know it works

The last test exercises **both sides**: it attempts a write from inside the
container, which must be refused, then queries the service from the `client`
Pod, which must answer. Both are in the same test: "the site answers" is
already true before you intervene, and an nginx that no longer starts writes
nowhere either.

```bash
dsoxlab check cks-security-context-immutable
```
