# Take back a privileged Pod in production, without stopping its work

## The situation

In the **`production`** namespace, the **`insecure-app`** Pod has been running
for weeks. It works, nobody complains, and that is precisely the problem: it
was created in a hurry with everything needed to "make it work".

An audit has just flagged it. It is yours to take back.

## What you must achieve

1. A Pod named **`secure-app`** in `production`, doing the same work as the
   original, and **running**.

2. It keeps **none** of `insecure-app`'s defects. There are several, and
   finding them is part of the exercise: read the original's full definition
   before writing anything.

3. The image is pinned to a **version**, not to a name that can change under
   you at the next restart.

4. **`insecure-app` no longer exists.** A fix placed next to the flaw fixes
   nothing.

## Useful bearings

`kubectl get pod insecure-app -o yaml` returns the full definition, including
what you did not write. That is where host namespace sharing, privileges and
process identity are read.

The `securityContext` exists at two levels, and not every field is accepted at
both: what concerns the user applies at Pod level as well as container level,
while privilege, escalation and capabilities are declared at container level
only.

A privileged container receives **all** kernel capabilities. Removing them one
by one makes no sense: you drop them all, then hand back those the application
needs, and an application that sleeps needs none.

## How you will know it works

The tests read the new Pod's definition, check the old one is gone, then step
inside the container. The last one is the only one that proves anything: it
**counts** the processes the container can see. With the host namespace, it
sees over a hundred, those of the whole node; without it, a handful.

```bash
dsoxlab check cks-secure-existing-pod
```
