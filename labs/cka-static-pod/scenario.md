# Place a static Pod on a worker, without going through the API

## The situation

The network team wants a status page served from the worker
**`k8s-w1.lab`** itself, one that stays up even when the API server is
unreachable. A Deployment will not do: with no API, nothing reschedules it.
What is needed is a Pod that the **worker's kubelet manages on its own**,
from a file placed on the node.

You are on the control plane. As in the exam, `ssh k8s-w1.lab` opens a
session on the worker.

## What you must achieve

1. On `k8s-w1.lab`, a Pod manifest dropped in the **directory the kubelet
   watches**. That directory is not to be guessed: the kubelet's own
   configuration names it.

2. The Pod is called **`static-web`**, runs in the `default` namespace,
   carries the label `role: static`, and its container, named `web`, uses
   the image **`nginx:1.27-alpine`** and exposes **port 80**.

3. The Pod shows up in the API, **`Running`**, under the name the kubelet
   gives to mirror Pods: the Pod name suffixed with the node name.

## Useful bearings

The kubelet does not create this Pod because someone asked through the API:
it creates it because it read a file, and it then publishes a **mirror Pod**
in the API so that you can see it, read-only. Deleting that mirror deletes
nothing: the kubelet recreates it. Only the file counts.

The watched path is a field of `/var/lib/kubelet/config.yaml`, the file
`kubeadm` wrote when the node joined. A malformed manifest shows up nowhere
in the API: it is the kubelet's journal, on the worker, that says what it
holds against it.

## How you will know it works

The tests read the file on the worker, the mirror Pod in the API, and ask
the worker's runtime whether it is really running the container.

```bash
dsoxlab check cka-static-pod
```
