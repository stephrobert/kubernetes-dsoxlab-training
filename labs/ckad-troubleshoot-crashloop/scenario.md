# Three Pods in CrashLoopBackOff, three causes

## The situation

In the **`lab`** namespace, three Pods have been restarting in a loop since
this morning: **`bad-command`**, **`missing-env`** and **`oom-killed`**.
Their names are not a hint, the previous team named them that way after the
fact, as it discovered the failures, and nobody fixed them.

Each one dies for a different reason, and each reason is read in a different
place: the container's exit message, its logs, or what the kubelet tells
about its last death.

## What you must achieve

1. `bad-command` runs: its start command exists and stays alive.

2. `missing-env` runs: it gets the environment variable it demands. Its logs
   say which one.

3. `oom-killed` runs: its memory limit is enough for nginx, at least
   **64Mi**, and it is no longer killed by the kernel.

4. The three Pods are **`Running`**, stable, and the restart counter no
   longer goes up.

## Useful bearings

`kubectl describe pod` shows, for each container, its last terminated state,
with a reason, `Error` or `OOMKilled`, and an exit code.
`kubectl logs --previous` shows what the container wrote before dying.

A bare Pod cannot be modified on those fields: the command, the variables
and the limits are frozen. It has to be recreated, with the same name.

## How you will know it works

The tests read the state of each Pod, its memory limit, and make sure the
restart counter no longer increases.

```bash
dsoxlab check ckad-troubleshoot-crashloop
```
