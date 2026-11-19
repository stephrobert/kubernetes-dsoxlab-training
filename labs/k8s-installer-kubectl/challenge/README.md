# Challenge: Install and configure kubectl

## 📍 The situation

On the `k8s-kind.lab` machine, a kind cluster named **`lab`** is running, on
Kubernetes **`v1.37.0`**. Your **`~/.kube/config`** file already knows how to
connect to it. You do not have to create this cluster: that is the subject of
the next lesson. All you lack is the tool to talk to it: **kubectl is not
installed**, and neither is its completion.

## 🎯 What you must obtain

1. **kubectl is installed in `/usr/local/bin`.** The file belongs to `root`.
   Everyone can run it, but only `root` can modify it. It is the one the shell
   finds when you type `kubectl`.

2. kubectl is **version 1.37**. The lesson uses **`v1.37.2`**.

3. It is **the official file**: its fingerprint is the one `dl.k8s.io`
   publishes. Check it before installing.

4. kubectl **completion** works in **every new terminal**.

5. The **`k` alias** runs kubectl, and the Tab key completes it like kubectl.

6. kubectl **reaches the cluster**.

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

The tests look at the installed file, its fingerprint, what a new terminal
sees, and the answer of the cluster.

```bash
dsoxlab check k8s-installer-kubectl
```

`dsoxlab clean k8s-installer-kubectl` then removes your alias and your
completion, and puts back on the machine the kubectl the next labs need.
