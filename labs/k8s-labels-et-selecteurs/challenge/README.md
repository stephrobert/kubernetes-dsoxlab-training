# Challenge: Label and select Pods

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. In the **`etiquettes`** namespace:

- the **`vitrine`** Deployment runs three Pods;
- the **`facturation`** Deployment runs two Pods;
- the **`outils`** Deployment runs one Pod, which carries the
  `palier=interne` label.

The Pods of `vitrine` and `facturation` have no `palier` label. The file
**`~/etiquettes/releve.txt`** is waiting for a selector.

## 🎯 What you must obtain

1. **All the Pods of `vitrine` have the `palier=front` label**, and they keep
   it when they are replaced.

2. **The `vitrine` Deployment has a `contact` annotation**, with a sentence
   that says who to contact when it fails.

3. After **`selecteur`**, in the file: a label selector that uses a negation
   (`!=` or `!key`) and returns **exactly the Pods of `facturation`**.

## 🧭 Useful landmarks

A label set on a Pod disappears with it. And the Pods of a Deployment are
replaced often: at every update, every deletion, every node failure. A label
that must last is therefore written in the Deployment's Pod template. A label
set on the Deployment itself does not go down to the Pods.

To choose between a label and an annotation, ask yourself whether you will
ever need to pick objects by this information. A contact sentence is not
used to pick, and a label accepts no spaces.

Try your selector with `kubectl get pods -n etiquettes -l` before writing it in
the file, and count the Pods it returns. Watch out: a negation also keeps the
Pods that do not have the key at all. Write the selector alone, as it comes
after `-l`.

## ✅ How you will know it is right

The tests read the Pod template and the annotations of `vitrine`. They then
replay your selector as it is and compare the Pods it returns with those of
`facturation`.

```bash
dsoxlab check k8s-labels-et-selecteurs
```
