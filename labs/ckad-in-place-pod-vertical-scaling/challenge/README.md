# Challenge: Resize a Pod in place, without restarting it

## 📍 The situation

The **`scaling-pod`** Pod in the **`lab`** namespace has been running for weeks
on a budget that has become too small: `100m` of CPU requested, `128Mi` of
memory as its limit. It holds a long session that must **not be interrupted**.
It needs more, now, without being created again and without its container
restarting.

The Pod was delivered with a resize policy that allows it.

## 🎯 What you must obtain

1. `scaling-pod` requests **`200m`** of CPU and is limited to **`256Mi`** of
   memory.
2. The Pod has **not been created again**: it is the same object, with the
   same creation date, and its container shows **zero restarts**.
3. The kernel enforces the new limit: read from inside the container, it is
   256Mi.

## 🧭 Useful landmarks

`kubectl edit` refuses to change the resources of a Pod: that field goes
through a dedicated **subresource**, which `kubectl patch` can target. The
Pod's status then shows the resources the kubelet really applied, which may
differ for a moment from the ones requested.

The memory limit a container is held to can be read in its cgroup.

## ✅ How you will know it works

The tests read the Pod's resources, its creation date, its restart counter,
and the limit in the container's cgroup.

```bash
dsoxlab check ckad-in-place-pod-vertical-scaling
```
