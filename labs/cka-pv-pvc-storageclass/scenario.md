# A persistent volume: PersistentVolume, PersistentVolumeClaim and a Pod that writes

## The situation

This cluster has **no StorageClass** and no provisioner: a volume claim
stays `Pending` on it forever. The team needs a Pod, **`data-pod`**, that
writes a file and finds it again when it is recreated. The
**`/mnt/lab-data`** directory exists on every node, reserved for this use.

You are on the control plane, with `kubectl` configured. The **`lab`**
namespace exists.

## What you must achieve

1. A PersistentVolume **`lab-pv`** of **1Gi**, in `ReadWriteOnce`, of
   StorageClass **`manual`**, backed by the node's `/mnt/lab-data`
   directory.

2. A PersistentVolumeClaim **`lab-pvc`** in `lab`, asking for **500Mi**
   with the same access mode and the same StorageClass, and which is
   **`Bound`** to `lab-pv`.

3. A Pod **`data-pod`** in `lab` that mounts this claim on **`/data`** and
   writes `hello` into **`/data/test.txt`** at startup.

4. The file is **on the node's disk**, in `/mnt/lab-data`, where the volume
   is backed: that is what will outlive the Pod.

## Useful bearings

With no provisioner, it is the administrator who creates the
PersistentVolume, and the claim binds to a volume whose capacity, access
mode and StorageClass suit it. A StorageClass named in a PV and a PVC does
not need to exist as an object: the name is enough to match them.

A volume backed by a node's disk is worth what that node is worth: the Pod
mounting it must run where the data is. `hostPath` does not enforce it,
`local` enforces it through a node affinity; both are accepted here.

## How you will know it works

The tests read the PV, the PVC and its binding, the Pod and its mount, the
file inside the Pod, then the same file on the node where the Pod runs.

```bash
dsoxlab check cka-pv-pvc-storageclass
```
