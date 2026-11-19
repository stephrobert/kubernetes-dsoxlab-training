# Challenge: Label and select Pods

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. In the **`etiquettes`** namespace:

- the **`web`** Deployment runs three Pods;
- the **`api`** Deployment runs two Pods.

None of these Pods has an `env` label. The file **`~/etiquettes/releve.txt`**
is waiting for a selector.

## 🎯 What you must obtain

1. **All the Pods of `web` have the `env=prod` label**, and they keep it when
   they are replaced.

2. **The `web` Deployment has a `description` annotation**, with a sentence
   that says what it is for.

3. After **`selecteur`**, in the file: a label selector that uses a negation
   (`!=` or `!key`) and returns **exactly the Pods of `api`**.

## 🧭 Useful landmarks

A label set on a Pod disappears with it. And the Pods of a Deployment are
replaced often: at every update, every deletion, every node failure. A label
that must last is therefore written in the Deployment's Pod template. A label
set on the Deployment itself does not go down to the Pods.

To choose between a label and an annotation, ask yourself whether you will
ever need to pick objects by this information. A description sentence is not
used to pick, and a label accepts no spaces.

Try your selector with `kubectl get pods -n etiquettes -l` before writing it in
the file, and count the Pods it returns. Watch out: a negation also keeps the
Pods that do not have the key at all. Write the selector alone, as it comes
after `-l`.

## ✅ How you will know it is right

The tests read the Pod template and the annotations of `web`. They then replay
your selector as it is and compare the Pods it returns with those of `api`.

```bash
dsoxlab check k8s-labels-et-selecteurs
```
