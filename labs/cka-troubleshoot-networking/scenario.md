# Repair a node's Pod network and read what the network says

## The situation

On the catalogue's kubeadm cluster, the worker **`k8s-w1.lab`** went
**NotReady** during the night. The Pod **`cible`**, an nginx placed on it in the
**`reseau`** namespace, stays in **`ContainerCreating`**. On the control plane,
the Pod **`sonde`** is waiting to reach it.

Two Services of the same namespace, **`stock`** and **`archives`**, do not
answer either, but each fails in its own way. The team wants to know which one
refuses and which one keeps you waiting.

The cluster's CNI is **Calico**. The **`~/reseau/`** directory is empty.

## What you must achieve

1. In **`~/reseau/plages.txt`**, a line **`pods: <range>`** and a line
   **`services: <range>`**: the Pod and Service address ranges of the **whole
   cluster**, as its configuration declares them.

2. In the same file, a line **`cible: <address>`**: the current address of the
   Pod `cible`.

3. The worker **`k8s-w1.lab`** is **Ready** again.

4. The Pod **`cible`** runs, **on the worker**.

5. The Pod **`sonde`**, on the control plane, **reaches `cible` by its
   address**, from one node to the other.

6. In **`~/reseau/verdicts.txt`**, a line **`stock: refus`** or
   **`stock: delai`**, and a line for **`archives`** of the same form: what each
   of the two Services really does.

## Useful bearings

A NotReady node gives its reason in its conditions. A Pod stuck in
`ContainerCreating` gives it in its events. Here both point to the same place:
the node's CNI configuration, under `/etc/cni/net.d/`, on the worker.

That file is not written by hand: the CNI's Pod, present on every node, sets it
up when it starts. A DaemonSet Pod recreates itself when deleted.

With Calico, the podCIDR written on a node does **not** tell where its Pods'
addresses come from: Calico draws them from small blocks of the cluster's pool.
The range that matters is the cluster's.

A refused connection fails **at once**. A connection to an address that does
not answer **waits** until the set timeout. Timing a request is enough to tell
them apart.

## How you will know it works

Each test checks one of the six states above. The fourth requires `cible` on
the worker: moving it to the control plane would work around the failure
without repairing it. The sixth compares with a draw made by the preparation:
the right verdict cannot be guessed.

```bash
dsoxlab check cka-troubleshoot-networking
```
