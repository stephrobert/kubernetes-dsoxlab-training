# Install and configure kubectl

## The situation

The machine `k8s-kind.lab` runs a kind cluster, **`lab`**, on Kubernetes
**`v1.37.0`**, and your **`~/.kube/config`** file already points to it. You do
not have to create this cluster: the next lesson teaches you how. What you lack
is the tool to talk to it: **kubectl is not installed**, and no completion is
configured.

## What you must obtain

1. **kubectl is installed in `/usr/local/bin`**, belongs to `root`, is
   executable by everyone and writable by root only, and it is the one your
   `PATH` finds.

2. The client is a **1.37 version**, pinned. The lesson uses **`v1.37.2`**.

3. The installed binary is **the official binary** of its version: its
   fingerprint is the one `dl.k8s.io` publishes, and you checked it before
   installing it.

4. kubectl **bash completion** is active in **every new shell**.

5. The **alias `k`** runs kubectl and **completes** like it.

6. kubectl **reaches the server** of the cluster.

## Useful landmarks

Never download "the latest version" without naming it: a pinned version
reinstalls identically, on your workstation as in a CI. The client and the
server may differ by **one minor version at most**, in either direction: a 1.37
client therefore talks to this 1.37.0 cluster.

A fingerprint is checked **before** installing, never after. It proves that the
file you received is the one the project published.

What you type in your shell disappears when it closes. A completion or an alias
meant for tomorrow is written in a file that bash reads at every start. To
check, open a **new** shell. On Debian, kubectl completion needs a package
that the lesson names: without it, Tab only offers file names.

`kubectl version` shows two versions, the client's and the server's. If the
second is missing, kubectl did not reach the cluster. `kubectl cluster-info`
tells at which address it looks for it.

## How you will know it works

The tests read the installed binary, its fingerprint, a new interactive shell
and the answer of the server.

```bash
dsoxlab check k8s-installer-kubectl
```

`dsoxlab clean k8s-installer-kubectl` removes your completion and your alias,
then puts back on the machine the kubectl the next labs need.
