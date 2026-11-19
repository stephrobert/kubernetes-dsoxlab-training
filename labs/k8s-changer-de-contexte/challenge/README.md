# Challenge: Switch context and set the default namespace

## 📍 The situation

Your kubectl targets the kind cluster **`boutique`**, through the
**`kind-boutique`** context. Your `~/.kube/config` file also knows a second
cluster, through the **`recette`** context. No default namespace is set.

The team asks you to work on the recette cluster from now on, in the
**`kube-system`** namespace, without having to give it on every command.

## 🎯 What you must achieve

1. The **context in use** is **`recette`**.

2. The **default namespace** of the `recette` context is **`kube-system`**.

3. A ConfigMap **`preuve`** exists. Create it with a command that gives
   **neither a context nor a namespace**: no `--context`, no `-n`. It must be
   in `kube-system`, on the recette cluster, and nowhere on the `boutique`
   cluster.

4. Your **`~/.kube/config`** is readable and writable **by you only**. It holds
   what it takes to act on both clusters, and today every account on the
   machine can read it.

## 🧭 Useful landmarks

All the useful commands start with `kubectl config`: list the contexts, see
the one in use, switch context, set the namespace of the context in use.
Careful: kubectl does not check that the namespace exists. Read back what you
typed.

The context switch is saved in the file: it applies to all your terminals. A
ConfigMap is created in one line, with a value written directly in the command
(`--from-literal`).

## ✅ How you will know it is right

The tests read your `~/.kube/config` and its permissions, then look for the
`preuve` ConfigMap on both clusters. It is only in the right place if the
context and the namespace are right.

```bash
dsoxlab check k8s-changer-de-contexte
```
