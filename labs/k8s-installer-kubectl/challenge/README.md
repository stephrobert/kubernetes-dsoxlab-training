# Challenge: Install and configure kubectl

## 📍 The situation

The machine `k8s-kind.lab` runs a kind cluster, **`lab`**, on Kubernetes
**`v1.37.0`**, and your **`~/.kube/config`** file already points to it. You do
not have to create this cluster: the next lesson teaches you how. What you lack
is the tool to talk to it: **kubectl is not installed**, and no completion is
configured.

## 🎯 What you must obtain

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

## 🧭 Useful landmarks

Write the version number in your commands, for example `v1.37.2`. Do not take
"the latest version" without knowing which one it is: tomorrow it will not be
the same. The kubectl client may be one minor version away from the cluster,
no more. A 1.37 kubectl is therefore fine for this 1.37.0 cluster.

Check the binary's fingerprint **before** installing it. If it does not match,
the downloaded file is not the one the project published: delete it and start
again.

A command typed in the terminal is forgotten when you close it. To keep the
alias and the completion, write them in `~/.bashrc`: bash reads this file every
time it starts. Then open a **new** terminal to check. On Debian, kubectl
completion also needs the `bash-completion` package. Without it, the Tab key
only offers file names.

To know whether kubectl reaches the cluster, run `kubectl version`. The
`Server Version` line must show. If it is missing, `kubectl cluster-info`
shows you at which address kubectl looks for the cluster.

## ✅ How you will know it works

The tests read the installed binary, its fingerprint, a new interactive shell
and the answer of the server.

```bash
dsoxlab check k8s-installer-kubectl
```

`dsoxlab clean k8s-installer-kubectl` removes your completion and your alias,
then puts back on the machine the kubectl the next labs need.
