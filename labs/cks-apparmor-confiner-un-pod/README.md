# Confine a Pod with an AppArmor profile

The lesson shows how to load an AppArmor profile on a node and apply it to a
Pod. This course adds what it only mentions: the profile the runtime sets when
you ask for nothing, a profile in **complain** mode that lets things through
and records them, its switch to **enforce** that refuses, and what happens
when a Pod asks for a profile that is missing from the node.

You work in the `essai-apparmor` namespace, with a test profile loaded on
`k8s-w1.lab`. The challenge targets another profile and another Pod: you will
do it on your own, at the end.

Related page: [AppArmor](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-apparmor-confiner-un-pod
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it, and `ssh` reaches the
workers. An AppArmor profile is loaded **on the node** where the Pod runs: the
Pods of this course are therefore placed on `k8s-w1.lab` (`nodeName`).

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2 and containerd on Ubuntu 24.04.

## 🛡️ Exercise 1: the profile a Pod gets without asking for anything

Start a Pod with no AppArmor setting at all, and read the profile of its main
process:

```bash
kubectl create namespace essai-apparmor; kubectl run defaut --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-apparmor --overrides='{"spec":{"nodeName":"k8s-w1.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/defaut -n essai-apparmor --timeout=60s; kubectl exec defaut -n essai-apparmor -- cat /proc/1/attr/current
```

```text
namespace/essai-apparmor created
pod/defaut created
pod/defaut condition met
cri-containerd.apparmor.d (enforce)
```

The Pod is not free: containerd applies its default profile,
`cri-containerd.apparmor.d`, in `enforce`. That profile already blocks
dangerous moves (mounting a filesystem, writing to some files of `/proc`). A
profile of your own does not start from nothing: it replaces this one.

## 👀 Exercise 2: a profile in complain mode

In **complain** mode, AppArmor forbids nothing: it lets things through and
records in the kernel log what it would have refused. It is the way to test a
profile on a real application without breaking it. Write a profile that only
allows reading everywhere, and writing to `/tmp`, `/dev` and `/proc`. The
`signal` rule lets the runtime send its signals to the container, so stop it.
Load it in complain mode on `k8s-w1.lab`:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'cat > /tmp/essai-lecture <<"AA"
#include <tunables/global>
profile essai-lecture flags=(attach_disconnected,mediate_deleted,complain) {
  #include <abstractions/base>
  signal,
  /{,**} rix,
  /tmp/{,**} rw,
  /dev/{,**} rw,
  /proc/{,**} rw,
}
AA
sudo apparmor_parser -r /tmp/essai-lecture; sudo aa-status | grep -A0 essai'
```

```text
   essai-lecture
```

Start a Pod under this profile, and write to `/etc`, which the profile does
not allow:

```bash
kubectl run prudent --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-apparmor --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"appArmorProfile":{"type":"Localhost","localhostProfile":"essai-lecture"}}}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/prudent -n essai-apparmor --timeout=60s; kubectl exec prudent -n essai-apparmor -- sh -c 'echo x > /etc/essai; echo écriture : code $?'; kubectl exec prudent -n essai-apparmor -- cat /proc/1/attr/current
```

```text
pod/prudent created
pod/prudent condition met
écriture : code 0
essai-lecture (complain)
```

The write succeeds (code 0), and the profile is indeed `essai-lecture
(complain)`. The kernel log of the node says what would have been refused:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo journalctl -k --since "-1 min" --no-pager | grep -m1 -oE "apparmor=.ALLOWED. operation=.[a-z]+. .*profile=.essai-lecture. name=.[^ ]+"'
```

```text
apparmor="ALLOWED" operation="mknod" class="file" profile="essai-lecture" name="/etc/essai"
```

`apparmor="ALLOWED"`: the creation of `/etc/essai` was let through, and
recorded. By reading these lines while the application runs, you learn which
rules are missing before switching to enforce.

Two traps found while preparing this course. An explicit `deny` rule applies
**even** in complain mode, and it leaves no trace in the log: to observe,
leave it out. And without the `signal` rule, the runtime can no longer stop
the container: deleting the Pod stays stuck.

## 🚫 Exercise 3: switch to enforce

Remove `complain` from the flags and reload the profile. The process of the
Pod, already running, gets the new rule at once:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sed -i "s/,complain)/)/" /tmp/essai-lecture; sudo apparmor_parser -r /tmp/essai-lecture'; kubectl exec prudent -n essai-apparmor -- sh -c 'echo x > /etc/essai2; echo écriture : code $?; echo y > /tmp/essai; echo écriture dans /tmp : code $?'; kubectl exec prudent -n essai-apparmor -- cat /proc/1/attr/current
```

```text
écriture : code 1
sh: line 0: can't create /etc/essai2: Permission denied
écriture dans /tmp : code 0
essai-lecture (enforce)
```

Writing to `/etc` is now refused, writing to `/tmp` still passes, and the
profile is in `enforce`. The log says so too:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo journalctl -k --since "-1 min" --no-pager | grep -m1 -oE "apparmor=.DENIED. operation=.[a-z]+. .*profile=.essai-lecture. name=.[^ ]+"'
```

```text
apparmor="DENIED" operation="mknod" class="file" profile="essai-lecture" name="/etc/essai2"
```

`apparmor="DENIED"`, on the same kind of operation. That is the line to look
for when a confined application fails on a "Permission denied" that file
permissions do not explain.

## ❓ Exercise 4: a profile that does not exist on the node

Ask for a profile that was loaded nowhere:

```bash
kubectl run ecoute --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-apparmor --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"appArmorProfile":{"type":"Localhost","localhostProfile":"essai-absent"}}}}' -- sleep 3600; sleep 10; kubectl get pod ecoute -n essai-apparmor; kubectl get pod ecoute -n essai-apparmor -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-200
```

```text
pod/ecoute created
NAME     READY   STATUS                 RESTARTS   AGE
ecoute   0/1     CreateContainerError   0          10s
failed to get container spec opts: failed to generate apparmor spec opts: apparmor profile not found essai-absent
```

The API server accepts the Pod, which then stays in `CreateContainerError`:
it is containerd, on the node, that cannot find the profile. The message names
it. On a cluster with several nodes, that is the typical symptom of a profile
loaded on one node and not on the one where the Pod was placed.

## 🧹 Clean-up

Delete the test namespace, then remove the profile from `k8s-w1.lab`:

```bash
kubectl delete namespace essai-apparmor --wait=true --timeout=180s; ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo apparmor_parser -R /tmp/essai-lecture; rm -f /tmp/essai-lecture; sudo aa-status | grep -c essai'
```

```text
namespace "essai-apparmor" deleted
0
```

`aa-status` no longer counts any test profile (0, with the code 1 `grep -c`
returns when it finds nothing).

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-apparmor-confiner-un-pod
dsoxlab check cks-apparmor-confiner-un-pod
```

```text
╭─ Result: cks-apparmor-confiner-un-pod ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests       │
╰────────────────────────────────────────╯
```

That is the expected result on a fresh lab. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a profile to load in enforce mode on the
right node, and a Pod to confine with it, with the proof that the confinement
works.

```bash
dsoxlab run cks-apparmor-confiner-un-pod
dsoxlab challenge cks-apparmor-confiner-un-pod
```
