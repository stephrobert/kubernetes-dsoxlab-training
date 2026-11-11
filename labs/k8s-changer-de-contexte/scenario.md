# Merge a kubeconfig and switch context

## The situation

Your `kubectl` targets the kind cluster **`boutique`** through the context
**`kind-boutique`**, written in `~/.kube/config`, a file currently readable by
every account on the machine. A colleague sent you access to
a second cluster: the file **`~/Downloads/kubeconfig-recette.yaml`**, left
there like a download, readable by everyone. Its context is named
`kind-recette`.

## What you must obtain

1. The received file is **stored** in **`~/.kube/configs/recette.yaml`**,
   readable by you alone, and it is **no longer** in `~/Downloads`.

2. `~/.kube/config` holds a context **`recette`** that targets the received
   cluster, **next to** `kind-boutique`, which must survive the operation.

3. The **active context** is `recette`.

4. The **default namespace** of the `recette` context is **`kube-system`**.

5. `~/.kube/config` is **readable by you alone**.

## Useful landmarks

Always read a received kubeconfig before using it: which address it sends your
commands to, under which context name, with which identity. The `KUBECONFIG`
variable, set in front of a command, applies to that command only.

Merging is not copying. Copying the received file over yours would lose
`kind-boutique`. The lesson shows how to list both files in `KUBECONFIG` and
flatten them into a single file, after a backup, without forgetting to unset
`KUBECONFIG` afterwards.

A file written by a redirection takes the default mode: check it with `ls -l`,
and restrict it. `kubectl config` can rename a context, switch, and set the
default namespace of the current context; it does not check that the namespace
exists, so read back what you wrote.

## How you will know it is right

The tests read your kubeconfig files and their modes.

```bash
dsoxlab check k8s-changer-de-contexte
```
