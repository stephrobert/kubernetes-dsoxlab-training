# Challenge: Extract fields with JSONPath and custom-columns

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. In the **`extraction`** namespace, the **`web`** Deployment
runs two nginx Pods, with the label `app=web`. An update of its image was
requested, but it was paused.

The file **`~/extraction/releve.txt`** is waiting for a value, and the
**`~/extraction/`** directory is waiting for your two lists.

## 🎯 What you must obtain

1. After **`image-modele`**, in the file: the image asked for by the **Pod
   template** of the `web` Deployment, as it is, digest included.

2. **`~/extraction/pods-jsonpath.txt`** lists, with **JSONPath**, each Pod of
   `web` followed by the **node** hosting it: one line per Pod, no title.

3. **`~/extraction/pods-colonnes.txt`** gives the same information with
   **custom-columns**: a title line, then one line per Pod.

## 🧭 Useful landmarks

To find the path of a field, first show the object in YAML and follow the
indentation. On a single object, the path starts at its root. On a list, the
objects are under `.items`, and `range … end` repeats a pattern for each one.
Without `{"\n"}`, JSONPath writes no line break. Single quotes stop the shell
from interpreting brackets, braces and commas.

The Deployment and its Pods do not necessarily say the same thing: a paused
update has already changed the template, without having replaced the Pods yet.
What is asked here is what the Deployment wants.

A kubectl output is redirected to a file, like any other.

## ✅ How you will know it is right

The tests compare your record file and your two lists with the Deployment and
its Pods.

```bash
dsoxlab check k8s-extraire-avec-kubectl
```
