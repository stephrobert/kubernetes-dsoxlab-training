# Bring down a CIS audit's count, and prove it with a second audit

## The situation

The cluster comes out of a default `kubeadm` install. The compliance team asks
for an audit against the **CIS benchmark**, and remediation of what can be
fixed without changing the architecture.

**kube-bench** is the tool for that audit. Its Job is already written, on the
node, at `/root/kube-bench-job.yaml`. It runs inside the cluster, with the
node's directories mounted read-only, and writes its report as JSON in its
logs.

## What you must achieve

1. You have **run the audit** and read what it holds against the control
   plane.

2. Checks **1.2.15**, **1.3.2** and **1.4.1** pass. They carry different
   numbers and one same complaint: it is for you to see which, and against
   which components.

3. The **control plane still works**: `kubectl get nodes` answers and the
   `kube-system` Pods are back to `Running`.

4. The **total** failure count has gone down. Fixing one check while breaking
   another does not count.

## Useful bearings

The three components involved are **static Pods**: their definitions are files
on the node, under `/etc/kubernetes/manifests/`, and the kubelet watches them.
Changing a file is enough to redeploy the Pod.

kube-bench's report is JSON in the Job Pod's logs. Each check carries its
number, its title, its state, and a `remediation` section saying what to do.

A Job that has already run does not restart: it must be deleted before being
recreated.

The audit can be rerun as often as you like. It is in fact the only way to
know whether a fix took effect.

## How you will know it works

The last test **reruns kube-bench** and counts. It does not reread a report
you might have left: a report can be edited, an audit running before our eyes
cannot. It requires the three targeted checks to pass, and the total failure
count to have gone down.

```bash
dsoxlab check cks-cis-benchmark-remediate
```
