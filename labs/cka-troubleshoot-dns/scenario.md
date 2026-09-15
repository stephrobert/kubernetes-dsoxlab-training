# Restore the cluster's DNS resolution

## The situation

A team calls you: their application no longer answers. It runs in the
**`app`** namespace and has nothing complicated about it: a **`web`** Pod
serving a page, a **`web-svc`** Service exposing it, and a **`client`** Pod
querying it by its name, `web-svc.app.svc.cluster.local`.

Nobody touched the application. The `web` Pod is running, the Service exists,
and yet the client reaches nothing: the name no longer resolves. It is not the
application that is broken, it is **something in the cluster**.

## What you must achieve

1. From the `client` Pod, the name `web-svc.app.svc.cluster.local` resolves
   again.

2. The `client` Pod reaches `web-svc` over HTTP by that name.

3. The component that resolves names in the cluster is **back in service**, in
   the state a kubeadm cluster leaves it in. A patch inside the `client` Pod
   does not count: it is the cluster you are asked to repair.

## Useful bearings

Name resolution in Kubernetes is not handled by the Pods themselves: each Pod
queries a Service in the **`kube-system`** namespace, whose address is written
in its `/etc/resolv.conf`. That Service, like every other one, only answers if
Pods stand behind it.

Start by observing the failure from the `client` Pod, then work your way up:
the Service, its endpoints, and what should be providing them.

## How you will know it works

The tests read the state of the **cluster**, not the commands you typed: they
look at the DNS component, then they really attempt a resolution and an HTTP
request from the `client` Pod.

```bash
dsoxlab check cka-troubleshoot-dns
```
