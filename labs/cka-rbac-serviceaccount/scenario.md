# Give an application an identity: ServiceAccount, Role, RoleBinding

## The situation

The application team has deployed **`inventaire`** in the **`app-team`**
namespace: a tool that must list the Pods of its namespace to keep their
inventory. The Deployment is there, but no Pod starts. The manifest declares
a ServiceAccount **`pod-reader`** that nobody created, and with no identity,
the ReplicaSet cannot launch anything.

Next to it runs **`affichage`**, which serves a static page and never calls
the API. Like any Pod, it received a ServiceAccount token it has no use for.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. The ServiceAccount **`pod-reader`** exists in `app-team`, and the
   `inventaire` Pod runs with that identity.

2. A Role **`pod-reader-role`** in `app-team`, allowing the Pods to be read:
   `get`, `list`, `watch`. Nothing else: neither deleting them, nor creating
   them, nor touching any other resource.

3. A RoleBinding **`pod-reader-binding`** in `app-team`, granting that Role
   to the ServiceAccount.

4. From the Pod, with the token it finds in
   `/var/run/secrets/kubernetes.io/serviceaccount`, listing the Pods of
   `app-team` answers `200`. Deleting a Pod, reading the Secrets, or listing
   the Pods of `default` answer `403`.

5. The running Pod of **`affichage`** carries **no token**: nothing is
   mounted in `/var/run/secrets/kubernetes.io/serviceaccount`. The
   `inventaire` Pod, which needs its token, keeps it.

## Useful bearings

A Pod never talks to the API in its own name: it presents its
ServiceAccount's token, projected into a volume, and the API identifies it
as `system:serviceaccount:<namespace>:<name>`. That subject, and not a user,
is what the RoleBinding must name.

`kubectl auth can-i <verb> <resource> -n <namespace> --as
system:serviceaccount:app-team:pod-reader` answers `yes` or `no` without
creating anything. The Pod, for its part, has `curl`, the API certificate
and its token at hand: `kubectl exec` takes you there.

A ReplicaSet that cannot create its Pods says so in the namespace events,
not in logs that do not exist yet.

A token is mounted when the Pod is created. Changing what decides it does not
remove it from a Pod that is already running.

## How you will know it works

The tests read the Role and the RoleBinding, then enter the Pod and query
the API with its token, for what must go through as well as for what must be
denied. They finally read the running Pod of `affichage`, to check that no
token is mounted in it.

```bash
dsoxlab check cka-rbac-serviceaccount
```
