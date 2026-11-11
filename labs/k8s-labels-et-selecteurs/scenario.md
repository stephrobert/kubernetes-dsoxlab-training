# Label and select Pods

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. In the **`etiquettes`** namespace, two Deployments run: **`web`**,
with three replicas, and **`api`**, with two. None of their Pods carries an
`env` label.

The record **`~/etiquettes/releve.txt`** waits for a selector.

## What you must obtain

1. **All the Pods of `web` carry the label `env=prod`**, and they keep it when
   they are replaced.

2. **The Deployment `web` carries a `description` annotation**, with a sentence
   that says what it is for.

3. **`selecteur`** holds a label selector that uses a negation (`!=` or `!key`)
   and returns **exactly the Pods of `api`**.

## Useful landmarks

A label put on a Pod lives and dies with that Pod. The Pods of a Deployment are
replaced at every update, every deletion, every node failure: a label that must
last is written where the Pods are made from. A label put on the Deployment
itself does not go down to the Pods.

Before choosing between a label and an annotation, ask the question that
decides: will objects ever have to be selected by this information? A
description sentence is not used to select, and a label accepts no spaces.

For the selector, try it with `kubectl get pods -n etiquettes -l` before
writing it down, and count what it returns: a negation also keeps the objects
that do not have the key at all.

## How you will know it is right

The tests read the Pod template and the annotations of `web`, then replay your
selector as it is.

```bash
dsoxlab check k8s-labels-et-selecteurs
```
