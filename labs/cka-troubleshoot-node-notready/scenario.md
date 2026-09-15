# Bring a NotReady node back into the cluster

## The situation

The worker **`k8s-w1.lab`** went **`NotReady`** this morning, and nobody knows
why. The control plane, for its part, is fine.

The **`web-app`** application, in the **`production`** namespace, must run
three replicas. It is **reserved for this worker** by a `nodeSelector`, for
licensing reasons: it has nowhere else to go. Since this morning, it has been
degraded.

You are on the control plane. As in the exam, `ssh k8s-w1.lab` opens a session
on the worker.

## What you must achieve

1. The `k8s-w1.lab` node is **`Ready`**.

2. The node's agent is **running**, and it **will survive a reboot** of the
   machine: repairing for an hour does not count.

3. The `web-app` Deployment has its **three replicas available**, on
   `k8s-w1.lab`.

## Useful bearings

A `NotReady` node is a node whose agent no longer reports to the control plane.
`kubectl describe node` says so in its conditions, with the time of the last
sign of life. The rest cannot be read from the control plane: you have to go to
the node, and question systemd there.

A service can be stopped in two ways, and one of the two does not show up in
`systemctl status`.

## How you will know it works

The tests read the node's state from the API, the state of the service on the
worker itself, and the state of the Deployment.

```bash
dsoxlab check cka-troubleshoot-node-notready
```
