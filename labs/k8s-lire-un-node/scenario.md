# Read what a worker Node declares

## The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your `kubectl` already points at it. The card
**`~/lire-un-node/fiche.txt`** waits for what the worker
**`architecture-worker2`** says about itself.

## What you must achieve

For the Node `architecture-worker2`:

1. **`runtime`** holds its container runtime and the version of that runtime.

2. **`version-kubelet`** holds the version of its kubelet.

3. **`cpu`** and **`memoire`** hold its CPU and memory **capacity**.

4. **`condition-ready`** holds the status of its **Ready** condition.

## Useful pointers

A Node is an object like any other: its kubelet keeps writing into it what
the machine offers and how it is doing. `kubectl get nodes -o wide` gives a
one-line summary per Node, runtime included; `kubectl describe node` gives the
whole card: **Conditions**, **Capacity** and **Allocatable**, then **System
Info**, where the kubelet and runtime versions are.

Capacity is what the machine has; Allocatable is what is left for Pods once
the system is served. The card asks for the **capacity**.

## How you will know it is right

The tests compare your card with what `architecture-worker2` declares at the
time of the check. Equivalent forms are accepted: a version with or without
its `v`, a memory in Ki, Mi or Gi.

```bash
dsoxlab check k8s-lire-un-node
```
