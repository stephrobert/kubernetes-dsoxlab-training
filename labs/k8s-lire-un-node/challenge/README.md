# Challenge: Read what a worker Node declares

## 📍 The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your kubectl already targets it. The **`~/lire-un-node/fiche.txt`** sheet
waits for what the **`architecture-worker2`** node says about itself.

## 🎯 What you must achieve

For the `architecture-worker2` node, fill in the sheet:

1. After **`runtime`**: the program that starts its containers, and its
   version.

2. After **`version-kubelet`**: the version of its kubelet.

3. After **`cpu`** and **`memoire`**: its processor and memory **capacity**.

4. After **`condition-ready`**: the value of its **Ready** condition.

## 🧭 Useful pointers

`kubectl get nodes -o wide` gives one line per node, with the runtime and the
kubelet version. `kubectl describe node` gives the whole sheet: the conditions
(`Conditions`), the capacity (`Capacity`), what is left for Pods
(`Allocatable`), then the versions (`System Info`).

`Capacity` is what the machine has. `Allocatable` is what is left for the
Pods. The sheet asks for the **capacity**.

## ✅ How you will know it is right

The tests compare your sheet with what `architecture-worker2` declares at
check time. Several ways of writing are accepted: a version with or without
its `v`, a memory in Ki, Mi or Gi.

```bash
dsoxlab check k8s-lire-un-node
```
