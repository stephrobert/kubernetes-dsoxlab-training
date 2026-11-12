# Switch context and set the default namespace

## The situation

Your `kubectl` points at the kind cluster **`boutique`** through the context
**`kind-boutique`**. Yet your `~/.kube/config` file knows a second cluster: the
context **`recette`** is already there, next to the first one. No default
namespace is set.

The team asks you to work on the recette cluster from now on, in the
**`kube-system`** namespace, without repeating it on every command.

## What you must achieve

1. The **active context** is **`recette`**.

2. The **default namespace** of the `recette` context is **`kube-system`**.

3. A ConfigMap **`preuve`** exists, created by a command that names **neither a
   context nor a namespace**: no `--context`, no `-n`. It must be in
   `kube-system` of the recette cluster, and nowhere in the `boutique` cluster.

## Useful landmarks

`kubectl config` reads and changes your kubeconfig: it can list the contexts,
say which one is active, switch from one to another, and set the default
namespace of the current context. It does not check that this namespace exists:
read back what you wrote.

The switch is written in the file, under `current-context`: it applies to all
your terminals and all your scripts. A ConfigMap is created in one line, with a
literal value.

## How you will know it is right

The tests read your `~/.kube/config`, then look for the ConfigMap `preuve` in
both clusters. It only lands in the right place if the switch and the default
namespace are right.

```bash
dsoxlab check k8s-changer-de-contexte
```
