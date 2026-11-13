# Prioritize Pods and watch a preemption

## The situation

On the kind cluster **`multi`**, the worker **`multi-worker`** is full: the
**`remplissage`** Deployment, in the **`ordonnancement`** namespace, runs four
Pods there that share all of its available CPU. None has a priority.

An urgent job must still run on that node. Its manifest waits for you in
**`~/lab/urgent.yaml`**: it requests exactly the room of one `remplissage` Pod,
and there is none.

## What you must achieve

1. Two PriorityClasses: **`basse`**, with value **1000**, and **`haute`**, with
   value **100000**. Neither is the cluster's default class.
2. The Pods of **`remplissage`** run under the class **`basse`**.
3. The Pod **`urgent`** runs on **`multi-worker`**, under the class
   **`haute`**.
4. To make room for it, the scheduler has **preempted** a `remplissage` Pod.

Do them in this order: the classes, then remplissage, then the urgent Pod.

## Useful bearings

A PriorityClass is a cluster object, with no namespace. A Pod names it with
`priorityClassName`, and admission turns that name into a numeric `priority`,
**when the Pod is created**: a Pod already running does not change priority.

When a Pod finds no room, the scheduler looks for lower-priority Pods whose
eviction would be enough. It evicts them, and says so with a **`Preempted`**
event on each victim. `kubectl get events -n ordonnancement` shows it.

## How you will know it works

The tests read both classes, the priority of the `remplissage` Pods and of the
urgent Pod, the node it runs on, and the preemption event.

```bash
dsoxlab check k8s-prioriser-et-preempter
```
