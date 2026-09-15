# Confine a Pod with an AppArmor profile

## The situation

You administer a cluster on which a team deploys a container whose code you
do not control. You want it to run, but you want it to be **impossible for
it to write in `/tmp`**, whatever the program inside does.

A plain `securityContext` does not answer that demand: it knows how to drop
capabilities, force a non-root user, make the root filesystem read-only, but
it does not know how to say "this process will never write in that precise
directory". That is the job of **AppArmor**, a security module of the Linux
kernel.

The profile is already dropped on the control plane **`k8s-cp.lab`**, in
`/etc/apparmor.d/k8s-refuser-ecriture`, and nowhere else. It is **not
loaded**: a profile file sitting on disk confines nothing as long as the
kernel has not read it. And a profile loaded on one node counts only on that
node: the Pod will have to run where the profile is.

## What you must achieve

1. The profile **`k8s-refuser-ecriture` is loaded** in the node's kernel, in
   **enforce** mode and not in `complain` mode.

2. A Pod named **`confine`** runs in the namespace **`confinement`**, on the
   node where the profile is loaded, and its container is **confined by that
   profile**.

3. The confinement is **effective**: a write in `/tmp` from that container
   is denied, while reading the filesystem works normally.

## Useful bearings

On the node, `aa-status` lists the loaded profiles and their mode. A profile
is loaded with `apparmor_parser`, and the flag you are interested in is the
one that replaces an already present profile.

On the Kubernetes side, attaching a profile to a container is declared **in
the `securityContext`** since 1.30. The annotation
`container.apparmor.security.beta.kubernetes.io/<container>` still works but
it is deprecated, and the exam expects the modern form.

The profile name declared on the Kubernetes side must match **exactly** the
one the kernel knows, which is not the file name but the one written after
the word `profile` in the file.

## How you will know it works

The test checks the state of the **system**, not the commands you typed: it
reads the profiles loaded on the node, the Pod definition, and it really
attempts a write in the container to see it denied.

```bash
dsoxlab check cks-apparmor-confiner-un-pod
```
