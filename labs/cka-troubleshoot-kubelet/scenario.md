# Repair a kubelet that refuses to start

## The situation

Last night, a colleague "just adjusted the DNS" on the worker
**`k8s-w1.lab`**. This morning, the node is **`NotReady`**, and `systemctl start
kubelet` changes nothing: the service comes back, then stops right away, again
and again.

The **`web-app`** application, in the **`production`** namespace, is reserved
for this worker by a `nodeSelector` and must run three replicas. It has been
degraded since the night.

You are on the control plane. As in the exam, `ssh k8s-w1.lab` opens a session
on the worker.

## What you must achieve

1. The `k8s-w1.lab` node is **`Ready`**.

2. The kubelet is **running**, with a **valid** configuration: the legitimate
   address of the cluster DNS, that of the `kube-dns` Service, must remain in
   it. Repairing by deleting the whole configuration is not repairing.

3. The `web-app` Deployment has its **three replicas available**, on
   `k8s-w1.lab`.

## Useful bearings

A service that stops as soon as it is launched says why in the journal, and the
kubelet is precise on that point: it names the file it cannot read, and the
line. On a kubeadm cluster, it reads its configuration from a YAML file under
`/var/lib/kubelet`, written by `kubeadm` when the node joined.

What `kubeadm` wrote is correct; what was added afterwards is not, neither in
its form nor in its content.

## How you will know it works

The tests read the node's state from the API, the state of the service and the
configuration file on the worker itself, and the state of the Deployment.

```bash
dsoxlab check cka-troubleshoot-kubelet
```
