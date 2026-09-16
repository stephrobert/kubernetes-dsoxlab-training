# Refuse a privileged Pod at admission, with Pod Security Admission

## The situation

The **`secure-ns`** namespace accepts anything. A Pod already runs there,
**`laxiste`**, and it proves the point: it shares the host's PID namespace and
its container runs as root. Nothing stopped it.

The security team wants the cluster to **refuse that kind of Pod at the moment
it is asked for**, rather than have it turn up later in an audit.

## What you must achieve

1. The `secure-ns` namespace applies the **`restricted`** standard in all three
   modes: the one that **blocks**, the one that **warns** and the one that
   **records**.

2. A Pod that violates the standard is **refused at admission**. You do not
   need to create one to check that, and you had better not.

3. A Pod named **`conforme`** runs in `secure-ns`, from the `busybox:1.37`
   image, and satisfies the restricted standard: non-root user, no privilege
   escalation, all capabilities dropped, and a seccomp profile declared.

4. The `laxiste` Pod **keeps running**. Leave it alone: what becomes of it
   once the standard is on is part of what this lab teaches.

## Useful bearings

The standard is switched on with **labels on the namespace**, not with a
dedicated object. The three modes are independent and may target different
levels.

`kubectl apply --dry-run=server` sends the object to the API server, which
runs it through **the whole admission chain**, then does not write it. That is
the clean way to check that a rule refuses something without dirtying the
cluster, and it is more reliable than `--dry-run=client`, which never leaves
your machine.

The `restricted` standard demands four things of a container, and the refusal
message names them one by one when they are missing.

## How you will know it works

The tests read the state of the cluster. The last one is the only one that
proves admission: it submits a forbidden Pod, which must be refused, **and** a
compliant one, which must be accepted. A policy that refuses everything would
fail it too.

```bash
dsoxlab check cks-pod-security-admission
```
