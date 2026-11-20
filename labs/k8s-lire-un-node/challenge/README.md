# Challenge: Read what a worker Node declares

## 📍 The situation

The kind cluster **`architecture`** runs one control plane and three workers.
Your kubectl already targets it. The **`~/lire-un-node/fiche.txt`** sheet
waits for what the **`architecture-worker2`** node says about itself.

## 🎯 What you must achieve

For the `architecture-worker2` node, fill in the sheet:

1. After **`adresse-interne`**: its internal IP address.

2. After **`plage-des-pods`**: the address range from which its Pods get their
   address.

3. After **`machine-id`**: its machine identifier.

4. After **`ready-depuis`**: the date and time it became **Ready**.

## 🧭 Useful pointers

`kubectl describe node` gives the whole sheet of a node, section by section:
the conditions (`Conditions`), the addresses (`Addresses`), the capacity
(`Capacity`), the versions and identifiers (`System Info`), then the Pod
address range (`PodCIDR`).

These four values belong to `architecture-worker2`: the other nodes have
other ones. Read the sheet of that node, and copy each value alone on its
line.

## ✅ How you will know it is right

The tests compare your sheet with what `architecture-worker2` declares at
check time. The time is copied as `kubectl describe node` shows it, or in the
`2026-11-20T07:28:14Z` format of `kubectl get -o yaml`.

```bash
dsoxlab check k8s-lire-un-node
```
