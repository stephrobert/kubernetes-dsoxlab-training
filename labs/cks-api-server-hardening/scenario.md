# Close the API server's profiler, without closing the API

## The situation

The cluster comes out of a default `kubeadm` install. Like every such cluster,
its API server exposes `/debug/pprof/`, the Go profiler: whoever reaches it
learns the memory usage, goroutine count and load of the cluster's most
sensitive component.

Nobody uses it, and it is open.

## What you must achieve

1. The profiler **no longer answers**.

2. Two other hardening settings are applied to the API server: **effective
   revocation of service account tokens**, and a **TLS version floor** at 1.2.

3. **The cluster still works.** `kubectl get nodes` answers, and the API
   server's static Pod is back to `Running`.

4. You do **not** add `--anonymous-auth=false`. That flag was not asked for,
   and it breaks this cluster: the reasons are in the hints if you want to
   know before trying it.

## Useful bearings

The API server is a **static Pod**. Its definition is a file on the node,
under `/etc/kubernetes/manifests/`, and the kubelet watches it: as soon as the
file changes, it redeploys the Pod. The API then vanishes for some ten
seconds, which is expected.

A flag refused at startup makes the container exit immediately, and the
kubelet restarts it in a loop. Meanwhile `kubectl` no longer answers, which
makes diagnosis uncomfortable: `sudo crictl ps -a | grep kube-apiserver` then
`sudo crictl logs <id>` give the exact line, without going through the API.

The original manifest is backed up by the setup under `/var/backups`. If you
get stuck, copying it back restores the cluster.

## How you will know it works

The last test exercises **both halves** of the requirement: `/debug/pprof/`
must return an error, **and** `/version` must answer normally. An API server
at a standstill closes the profiler just as surely as a well-placed flag, and
that is hardening's most common contradiction.

```bash
dsoxlab check cks-api-server-hardening
```
