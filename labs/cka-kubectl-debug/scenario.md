# Get inside a container with no shell using kubectl debug

## The situation

In the namespace **`lab`**, a team runs its own DNS resolver, the Pod
**`distroless-app`**. Its image is built on CoreDNS, and it is **distroless**:
a single static binary, no shell, no `ls`, no `ps`. That is a good security
practice, until the day you have to look at what is going on inside.
`kubectl exec` answers that `sh` does not exist, and the logs say nothing about
what the process is doing.

The team asks you for two things. First, get the list of the processes that are
**really** running in that container, seen from the inside. Then, one notch
deeper: drop a witness file on the node itself, **without opening an SSH
session**, as you would on a managed node that nobody has direct access to.

## What you must achieve

1. The Pod `distroless-app` carries an ephemeral container named
   **`debugger`**, which shares the process namespace of the container
   `distroless-app`.

2. From that container, the list of processes has been written to
   **`/tmp/debug-output.txt`**: the `coredns` process of the application must
   be readable in it. The `debugger` container **stays alive**, so that the
   file can be read again.

3. A debug Pod for the node **`k8s-cp.lab`** exists and is running, with the
   access to the node's processes and filesystem that `kubectl` gives it.

4. Through that Pod, the file **`/tmp/node-debug.txt`** has been written **on
   the node itself**, with the content `node-debug-ok`. On the node, not in the
   Pod.

## Useful bearings

An ephemeral container is added to a running Pod, without restarting it, and
can never be removed from it. It sees the processes of another container only
if you ask for it explicitly.

A node debug Pod mounts the root of the node under a directory of the Pod. What
is written in the `/tmp` of the Pod disappears with it; what is written under
that mount point stays on the node.

The tooling image does not matter, as long as it has a shell and `ps`: busybox
is enough.

## How you will know it works

The tests read the definition of the Pod, read back the file in the `debugger`
container, look for a Pod that has access to the node, and read
`/tmp/node-debug.txt` directly on `k8s-cp.lab`.

```bash
dsoxlab check cka-kubectl-debug
```
