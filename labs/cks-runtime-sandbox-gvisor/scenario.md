# Isolate a Pod from the host kernel, and prove it by reading its version

## The situation

An ordinary container shares the **machine's kernel** with every other one,
and with the node itself. A flaw in that kernel is a flaw for everything
running on it.

The security team wants a sensitive workload to run in a **sandbox**: a
runtime that places its own application kernel between the container and the
machine.

The node is ready. `containerd` now knows **two** runtimes: the default one,
and a second named `runsc`. In the **`bac-a-sable`** namespace, a Pod named
**`ordinaire`** already runs with the default runtime: that is your comparison
point, leave it alone.

## What you must achieve

1. An object declaring the second runtime to the cluster, under the name
   **`gvisor`**. Its handler must match exactly the name `containerd` uses.

2. A Pod named **`confine`** in `bac-a-sable`, image `busybox:1.37`, running
   in that sandbox and **Running**.

3. From inside that Pod, the kernel version is **not** the machine's.

4. The `ordinaire` Pod still reads the machine's kernel.

## Useful bearings

The object bridging a name used by Pods and a runtime known to `containerd`
has **no namespace**: it applies cluster-wide.

The name `containerd` gives the runtime is found in its configuration, under
`/etc/containerd/config.toml`. It is not necessarily the one you will choose
for the Kubernetes object, and bridging the two is precisely what that object
does.

A Pod whose requested runtime is unknown to `containerd` does not start and
**stays pending**, with no obvious message: `kubectl describe pod` says so in
its events.

The field choosing a Pod's runtime cannot be changed on an existing Pod. It
must be recreated.

`cat /proc/version` inside a container says which kernel it sees. `uname -r`
on the node says the machine's.

## How you will know it works

The last test compares the kernel seen by **both** Pods, and the machine's. It
does not look for a particular word: it observes that the sandboxed Pod and
the ordinary one do not read the same kernel, and that the latter does read
the node's. Without that comparison point, the measurement would mean nothing.

```bash
dsoxlab check cks-runtime-sandbox-gvisor
```
