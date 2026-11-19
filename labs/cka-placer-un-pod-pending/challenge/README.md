# Challenge: Read why four Pods stay Pending and get each one placed

## The situation

The kubeadm cluster has three nodes: the control plane `k8s-cp.lab` and two
workers, `k8s-w1.lab` and `k8s-w2.lab`. This morning the team deployed four
applications in the namespace **`placement`**. None of them started: their
Pods stay **Pending**, and `kubectl get pods` does not say why.

What the team knows about its needs:

- **`calcul`** is a small computing service. Someone copied its CPU request
  from a high-performance computing machine.
- **`cache`** needs the **NVMe disk**. It is mounted on **`k8s-w2.lab`**, and
  on no other node.
- **`batch`** runs on **`k8s-w1.lab`**, the node the batch team reserved for
  itself: nobody else may settle there.
- **`archives`** keeps its files on a volume of the storage class **`lente`**,
  which the team asked for on purpose. The cluster has no dynamic
  provisioner: a volume of that class is declared by hand, for instance a
  `hostPath` under `/srv/archives`.

You are on the control plane, with `kubectl` configured, as root.

## What you must achieve

1. A **ConfigMap `diagnostic`** in `placement` holds one key per application,
   `calcul`, `cache`, `batch` and `archives`, and for each the cause of its
   blocking, in one word: `ressources`, `selecteur`, `taint` or `volume`.
2. **`calcul`** runs, with a CPU request a node can give.
3. **`cache`** runs on `k8s-w2.lab`, and keeps its NVMe disk requirement.
4. **`batch`** runs on `k8s-w1.lab`, and the node stays reserved.
5. **`archives`** runs, its volume `archives-data` is bound in the class
   `lente`, and the application can write to it.

## Landmarks

The method of the lesson, in four steps: spot the Pending Pods, read the
**`FailedScheduling`** event of each one, cross it with the state of the nodes
(labels, taints, capacity) and of the volumes, then fix and check.

The message of a `FailedScheduling` says why **every** node was rejected. Part
of these reasons is **background noise**: a node rejected because the Pod asks
for another one is not the cause of the blocking. The cause is the reason that
rejects the nodes this Pod could really use.

A right fix does not remove the constraint that blocks: it satisfies it.
Removing a `nodeSelector` or a taint would start the Pod, at the cost of what
the team had asked for.

## How you will know it works

The tests read the diagnostic ConfigMap, then, for each application, check
that a Pod is ready, on the right node, and that the original constraint is
still there. For `archives`, they write a file to the volume.

```bash
dsoxlab check cka-placer-un-pod-pending
```
