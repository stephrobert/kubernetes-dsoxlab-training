# Challenge: Isolate an application in a namespace

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. A colleague deployed the **`inventaire`** application (a
Deployment of two Pods and its Service on port 8080) without `-n`: it is in
**`default`**. The **`stock`** namespace, which was meant to receive it, is
empty. In the **`caisse`** namespace, the **`caisse`** Pod is running: it is
the one that must reach the inventory. The file **`~/namespaces/releve.txt`**
waits for what you will observe.

## 🎯 What you must obtain

1. The **`inventaire`** Deployment and its **`inventaire`** Service are in
   **`stock`**, with the same image and the same command as those of
   `default`, on port 8080. **Nothing** is named `inventaire` in `default` any
   more.

2. From the `caisse` Pod, the inventory answers by its **name followed by the
   namespace**, on the `/hostname` path of port 8080. This path returns the
   name of the Pod that answers. After **`pod-qui-repond`**, in the file: this
   name.

3. From the same Pod, the **short name** `inventaire` fails. After
   **`nom-court`**, in the file: what you observed.

## 🧭 Useful landmarks

An object does not change namespace: you create it again in the right one,
then remove the old one. `kubectl get deployment inventaire -o yaml` shows the
image and the command to reuse.

The short name of a Service is only found in the namespace of the Pod looking
for it. A request that should fail is run with a short timeout, so as not to
wait.

## ✅ How you will know it is right

The tests read the objects of `stock` and `default` and your file, then replay
both requests from the `caisse` Pod.

```bash
dsoxlab check k8s-isoler-par-namespace
```
