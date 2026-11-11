# An agent on every node, including the control plane

## The situation

The monitoring team wants an agent on **every node** of the cluster, one that
signals its presence in its logs. The control plane **`k8s-cp.lab`** is
protected, as it should be, by the taint
`node-role.kubernetes.io/control-plane:NoSchedule`: nothing is scheduled there
without saying so explicitly. The agent must still run on it too.

You are on the control plane, with `kubectl` configured. The namespace
**`monitoring`** exists.

## What you must achieve

1. A DaemonSet **`monitor-agent`** in `monitoring`, image
   **`busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`**, whose container writes `heartbeat` to its logs every
   sixty seconds, forever.

2. Its Pods carry the label **`app: monitor`**.

3. A Pod of that DaemonSet runs on **every node**, `k8s-cp.lab` included,
   **without removing the taint** from the control plane.

## Useful bearings

A DaemonSet does not pick nodes: it puts one wherever its Pod is admitted. A
`NoSchedule` taint turns away any Pod that does not tolerate it, and the
toleration is written in the DaemonSet template, key, operator and effect,
copied from what the node shows of its taint.

A DaemonSet that is missing a node says so in its status: the number of Pods
desired, scheduled and ready.

## How you will know it works

The tests read the DaemonSet and its status, the node of each Pod, the control
plane taint, and the logs of each agent.

```bash
dsoxlab check cka-daemonset-all-nodes
```
