# Extract fields with JSONPath and custom-columns

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. In the **`extraction`** namespace, the Deployment **`web`** runs two
nginx Pods, label `app=web`. An update of its image was requested, but its
rollout was paused.

The record **`~/extraction/releve.txt`** waits for a value, and the directory
**`~/extraction/`** for your two lists.

## What you must obtain

1. **`image-modele`** gives the image the **Pod template** of the `web`
   Deployment asks for, as it is, digest included.

2. **`~/extraction/pods-jsonpath.txt`** lists, with **JSONPath**, each Pod of
   `web` followed by the **node** that hosts it: one line per Pod, no header.

3. **`~/extraction/pods-colonnes.txt`** gives the same information with
   **custom-columns**: a header line, then one line per Pod.

## Useful landmarks

To find the path of a field, display the object in YAML first and follow the
indentation. On a single object, the path starts from its root; on a list, the
objects are under `.items`, and `range ... end` repeats a pattern for each one.
Without `{"\n"}`, JSONPath writes no newline. Quotes keep the shell from
interpreting brackets, braces and commas.

The Deployment and its Pods do not necessarily say the same thing: a paused
rollout has already changed its template, without replacing its Pods yet. What
is asked here is what the Deployment wants.

A kubectl output is redirected into a file like any other.

## How you will know it is right

The tests compare your record and your two files with the Deployment and its
Pods.

```bash
dsoxlab check k8s-extraire-avec-kubectl
```
