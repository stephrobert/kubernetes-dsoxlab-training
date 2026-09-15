# Resize a Pod in place, without restarting it

## The situation

The Pod **`scaling-pod`** in the **`lab`** namespace has been running for weeks
on a budget that has grown too tight: `100m` of CPU requested, `128Mi` of
memory as its limit. It holds a long session that must **not be interrupted**.
It needs more, now, without being recreated and without its container
restarting.

The Pod was shipped with a resize policy that allows it. For a long time,
changing the resources of a Pod meant deleting it; that is no longer true.

## What you must achieve

1. `scaling-pod` requests **`200m`** of CPU and is limited to **`256Mi`** of
   memory.

2. The Pod has **not been recreated**: it is the same object, with the same
   creation timestamp, and its container shows **zero restarts**.

3. The kernel applies the new limit: read from inside the container, it is
   256Mi.

## Useful bearings

`kubectl edit` refuses to change the resources of a Pod: that field goes
through a dedicated **subresource**, which `kubectl patch` knows how to target.
The Pod status then reports the resources actually allocated by the kubelet,
which may differ for a moment from those requested.

The memory limit a container is subject to can be read from its cgroup.

## How you will know it works

The tests read the resources of the Pod, its creation timestamp, its restart
counter, and the limit in the container cgroup.

```bash
dsoxlab check ckad-in-place-pod-vertical-scaling
```
