# Bring the API server back into service

## The situation

For the past few minutes, `kubectl` has stopped answering on the cluster:
`connection refused` on port 6443 of the control plane. Nothing has been
deployed. A colleague admits having "just tweaked an API server flag" for a
security test, right before leaving.

The control plane **`k8s-cp.lab`** is reachable: you are on it. The API is
not, and everything `kubectl` can do is out of service along with it.

## What you must achieve

1. The API server **answers**: `kubectl get nodes` works, and `/healthz`
   returns `ok`.

2. The static Pod **`kube-apiserver-k8s-cp.lab`** runs in `kube-system`,
   without restarting in a loop.

3. The API server manifest no longer carries the offending flag, and it
   still authorizes with **`Node,RBAC`**: an API server that starts by
   accepting everybody is not repaired, it is wide open.

## Useful bearings

On a kubeadm cluster, the API server is not a systemd service: it is a
**static Pod**, whose definition the kubelet reads from a manifest directory
and which it redeploys as soon as the file changes. No need for `kubectl` to
restart it: fixing the file is enough.

With no API, `kubectl` is blind, but the node is not: the container runtime
sees the containers, dead or alive, and keeps their logs; the kubelet
recounts in `journalctl` what it is trying to start.

## How you will know it works

The tests query the API, read the state of the static Pod, and reread the
manifest on the node to check that the authorization is still there.

```bash
dsoxlab check cka-troubleshoot-apiserver
```
