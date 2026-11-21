# Challenge: Bring down a CIS audit count, and check it with a second audit

## The situation

The cluster comes out of a default `kubeadm` installation. The compliance team
asks for an audit of the **`k8s-w1.lab`** worker against the **CIS
benchmark**, and the remediation of what can be fixed without changing the
architecture.

**kube-bench** is the tool that runs this audit. Its Job is already written,
on the control plane, in `/root/kube-bench-job.yaml`. It runs on `k8s-w1.lab`,
with the `node` target and the node's directories mounted read-only, and
writes its report as JSON in its logs.

## What you must achieve

1. You have **run the audit** of the worker and read what it holds against it.

2. Checks **4.1.1** and **4.1.9** pass. They have different numbers and the
   same flaw: up to you to see which one, and on which files.

3. The **worker still works**: `k8s-w1.lab` is `Ready`.

4. The worker's **total** failure count went down. Fixing one check by
   breaking another does not count.

## Useful bearings

The remediation is run **on the audited node**. From the control plane,
`ssh k8s-w1.lab` takes you there.

kube-bench's report is JSON in the logs of the Job's Pod. Each check carries
its number, its title, its status, and a `remediation` section that says what
to do.

A Job that has already run does not start again: it must be deleted before
being created again.

The audit can be run again as often as you like. It is even the only way to
know whether a fix took.

## How you will know it works

The tests **run kube-bench again** on the worker and count. They do not read a
report you would have left: a report can be edited, an audit running in front
of us cannot. They require both target checks to pass, the failure total to
have gone down, and the worker to still be `Ready`.

```bash
dsoxlab check cks-cis-benchmark-remediate
```
