# Challenge: unblock a namespace, then validate and modify at admission without a webhook

## 🧭 The situation

The workshop team can no longer create a single Pod in its **`ateliers`**
namespace. Every `kubectl run` or `kubectl apply` there fails. The platform
team had installed an in-house controller that checked the Pods of this
namespace. It was uninstalled last week.

Once the namespace is unblocked, the platform team wants two rules, without
running a controller again:

- every Pod created in `ateliers` carries the label `equipe: ateliers`, even
  when its manifest forgets it;
- no privileged container (`privileged: true`) is accepted in `ateliers`.

The **`ateliers-temoin`** namespace is the control group. Neither rule must
apply there.

## 🎯 What you must achieve

1. The webhook that blocked `ateliers` is **deleted**, and an ordinary Pod is
   accepted there again.
2. A Pod submitted to `ateliers` **without any label** comes out with the
   label `equipe=ateliers`. A Pod of `ateliers-temoin` does not get it.
3. In `ateliers`, a Pod with a privileged container is **refused** by an API
   server policy. This is also true when the privileged container is an init
   container (`initContainers`). An ordinary Pod is still accepted, and a
   privileged Pod is still accepted in `ateliers-temoin`.

## 🔎 Useful pointers

Start by reading the full error message of a Pod creation in `ateliers`. It
names the webhook and the Service it calls. Then check whether that Service
has Pods behind it.

Both rules are set without a webhook or a controller, with the two native
policy types the lesson shows: a policy that modifies, a policy that
validates. Each one needs its binding to act.

To test a rule without creating a Pod, add `--dry-run=server` to your
command: the request goes through the whole admission chain, but nothing is
stored.

Give the API server a few seconds after each change before concluding.

## ✅ How you will know it works

The tests submit real Pods to the API server, with `--dry-run=server`: a Pod
without labels, a privileged Pod, a Pod with a privileged init container and
an ordinary Pod, in both namespaces. They read what the API server accepts,
refuses or modifies.

```bash
dsoxlab check k8s-valider-et-modifier-a-l-admission
```
