# Forbid one system call to a container, and prove it from the inside

## The situation

In the **`confinement`** namespace, the **`temoin`** Pod runs with no
restriction at all: like any container by default, it can ask the kernel for
whatever it wants, including changing file permissions.

The security team wants a sensitive application to be unable to call the
`chmod` family, without preventing it from working.

## What you must achieve

1. A seccomp profile named **`restrict-chmod.json`**, placed on the node where
   the kubelet looks for local profiles. It **allows everything by default**
   and **refuses** the `chmod` family.

2. A Pod named **`seccomp-pod`** in `confinement`, image `busybox:1.37`, which
   declares that profile and which **runs**.

3. Inside that Pod, a `chmod` **fails**, and everything else keeps working:
   creating a file, for instance, must still succeed.

4. The **`temoin`** Pod is not confined and can still call `chmod`. Leave it
   alone: it is the comparison point.

## Useful bearings

A seccomp profile is **not a Kubernetes object**. It is a JSON file on the
node, which the kubelet reads from a directory only it knows about, and the
path declared in the Pod is **relative** to that directory.

The `defaultAction` field decides what happens to the calls that are **not
named**. Denying by default would mean listing the hundreds of calls a
container needs just to start.

A family of calls often has more than one name. `chmod` is the best example: a
modern C library goes through another call of the same group, and filtering
only the first protects nothing.

A call refused by seccomp returns **EPERM**, which the shell shows as
"Operation not permitted".

## How you will know it works

The tests read the profile on the node, the Pod definition, then step inside
the container. The last one is the only one that proves the confinement, and
it exercises **both sides**: what is forbidden must fail, and what stays
allowed must keep working. An empty profile would pass the first two tests; a
profile refusing everything would break the container.

```bash
dsoxlab check cks-seccomp-profile
```
