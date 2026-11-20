# Label and select Pods

A **label** is a `key=value` tag set on a Kubernetes object. It is used to
**sort and pick** objects: a Service or a ReplicaSet finds its Pods by their
labels. An **annotation** looks like a label, but it is only used to
**document**: you cannot pick objects with it. The lesson sets labels one by
one and filters with `=` and `!=`. This course makes you act on several
objects at once with `-l`, use the `in` and `notin` selectors and the absence
of a key, and read where a lasting label is stored.

You work in a scratch namespace, `essai-labels`, with three Deployments,
`panier`, `stock` and `journal`. The challenge will ask you for the same kind
of work on other objects: you will do it on your own, at the end.

Related page: [Kubernetes labels and annotations: kubectl label and annotate](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-label-and-annotate/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-labels-et-selecteurs
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` runs there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: label several objects at once

Create the scratch namespace and three Deployments:

```bash
kubectl create namespace essai-labels
kubectl create deployment panier \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=2 -n essai-labels
kubectl create deployment stock \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=2 -n essai-labels
kubectl create deployment journal \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=1 -n essai-labels
```

```text
namespace/essai-labels created
deployment.apps/panier created
deployment.apps/stock created
deployment.apps/journal created
```

`kubectl label` accepts a selector instead of a name: it then labels every
object picked. The `in` selector picks the objects whose value is part of a
list. Set `equipe=ventes` on `panier` and `stock` in one command, then
`equipe=exploitation` on `journal`:

```bash
kubectl label deployments -n essai-labels -l "app in (panier,stock)" equipe=ventes
kubectl label deployment journal -n essai-labels equipe=exploitation
kubectl get deployments -n essai-labels -L equipe
```

```text
deployment.apps/panier labeled
deployment.apps/stock labeled
deployment.apps/journal labeled
NAME      READY   UP-TO-DATE   AVAILABLE   AGE   EQUIPE
journal   1/1     1            1           1s    exploitation
panier    2/2     2            2           2s    ventes
stock     2/2     2            2           1s    ventes
```

The `-L equipe` option adds a column with the value of that key.

## 📚 Exercise 2: pick with `notin` and the absence of a key

`notin` is the opposite of `in`. Then remove the label of `journal`, and
compare four selectors:

```bash
kubectl get deployments -n essai-labels -l "equipe notin (exploitation)"
kubectl label deployment journal -n essai-labels equipe-
kubectl get deployments -n essai-labels -l "equipe notin (ventes)"
kubectl get deployments -n essai-labels -l "equipe!=ventes"
kubectl get deployments -n essai-labels -l "!equipe"
kubectl get deployments -n essai-labels -l "equipe"
```

```text
NAME     READY   UP-TO-DATE   AVAILABLE   AGE
panier   2/2     2            2           2s
stock    2/2     2            2           1s
deployment.apps/journal unlabeled
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
journal   1/1     1            1           1s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
journal   1/1     1            1           1s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
journal   1/1     1            1           1s
NAME     READY   UP-TO-DATE   AVAILABLE   AGE
panier   2/2     2            2           2s
stock    2/2     2            2           1s
```

`journal` no longer has an `equipe` key, and yet `notin (ventes)` and
`!= ventes` return it: a negation also keeps the objects that do not have the
key at all. `!equipe` only picks the objects without the key, and `equipe`
alone those that have it, whatever its value. Before trusting a negation,
look at what it returns.

## 📚 Exercise 3: see where a lasting label lives

The labels of exercise 1 are on the Deployments. Look at those of the Pods of
`stock`:

```bash
kubectl get pods -n essai-labels -l app=stock --show-labels
```

```text
NAME                     READY   STATUS    RESTARTS   AGE   LABELS
stock-565d974c88-jpx84   1/1     Running   0          1s    app=stock,pod-template-hash=565d974c88
stock-565d974c88-xr8rp   1/1     Running   0          1s    app=stock,pod-template-hash=565d974c88
```

No `equipe`: a label set on a Deployment does not go down to its Pods. The
Pods are built from the Deployment's **template**. Write `niveau=critique`
there, wait for the Pods to be replaced, then compare both places:

```bash
kubectl patch deployment stock -n essai-labels \
  -p '{"spec":{"template":{"metadata":{"labels":{"niveau":"critique"}}}}}'
kubectl rollout status deployment/stock -n essai-labels --timeout=120s
kubectl get deployment stock -n essai-labels -o jsonpath='{.spec.template.metadata.labels}{"\n"}'
kubectl get deployment stock -n essai-labels -o jsonpath='{.metadata.labels}{"\n"}'
kubectl get pods -n essai-labels -l niveau=critique
```

```text title="Excerpt of the output"
deployment.apps/stock patched
deployment "stock" successfully rolled out
{"app":"stock","niveau":"critique"}
{"app":"stock","equipe":"ventes"}
NAME                    READY   STATUS    RESTARTS   AGE
stock-6bb545dd4-8vs9f   1/1     Running   0          2s
stock-6bb545dd4-8wc75   1/1     Running   0          1s
```

`spec.template.metadata.labels` carries `niveau=critique`: that is where new
Pods take their labels from, and every replaced Pod will get it.
`metadata.labels`, the labels of the Deployment itself, carries
`equipe=ventes`. Adding a label to the template changes the template: both
Pods were replaced, their name changed.

## 📚 Exercise 4: act on every object picked

A selector is also used to delete or annotate. Delete every Pod of `panier`
at once:

```bash
kubectl delete pods -n essai-labels -l app=panier
kubectl get pods -n essai-labels -l app=panier
```

```text
pod "panier-686df6f77c-lrcrq" deleted from essai-labels namespace
pod "panier-686df6f77c-t8rtz" deleted from essai-labels namespace
NAME                      READY   STATUS    RESTARTS   AGE
panier-686df6f77c-bbqng   1/1     Running   0          1s
panier-686df6f77c-pfvxj   1/1     Running   0          1s
```

The Deployment replaced them at once. Now annotate the Deployments of the
ventes team, then try to pick by that annotation:

```bash
kubectl annotate deployments -n essai-labels -l equipe=ventes revue="relu le 20 novembre 2026"
kubectl get deployments -n essai-labels -o custom-columns=NOM:.metadata.name,REVUE:.metadata.annotations.revue
kubectl get deployments -n essai-labels -l revue
```

```text
deployment.apps/panier annotated
deployment.apps/stock annotated
NOM       REVUE
journal   <none>
panier    relu le 20 novembre 2026
stock     relu le 20 novembre 2026
No resources found in essai-labels namespace.
```

The annotation accepts a sentence with spaces, which a label refuses. But
`-l revue` finds nothing: a selector only reads labels, never annotations.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace,
with its three Deployments.

```bash
kubectl delete namespace essai-labels
```

```text
namespace "essai-labels" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-labels-et-selecteurs
dsoxlab check k8s-labels-et-selecteurs
```

```text
╭─ Result: k8s-labels-et-selecteurs ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests   │
╰────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: label an application's Pods for good,
document its Deployment, and write a selector with a negation.

```bash
dsoxlab run k8s-labels-et-selecteurs
dsoxlab challenge k8s-labels-et-selecteurs
```
