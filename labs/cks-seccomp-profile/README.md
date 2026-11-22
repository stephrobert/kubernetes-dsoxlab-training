# Filter the system calls of a Pod with a seccomp profile

The lesson shows how to apply `RuntimeDefault`, write an allow-list
`Localhost` profile, and check the filter in `/proc`. This course adds three
cases it does not show: a profile that refuses a single family of calls and
lets the rest through, an unreadable profile file and the error it causes, and
an init container confined apart from the main container.

You work in the `essai-seccomp` namespace, with two test profiles placed on
`k8s-w1.lab`. The challenge targets another profile and other Pods: you will
do it on your own, at the end.

Related page: [Seccomp](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/seccomp/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-seccomp-profile
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it, and `ssh` reaches the
workers. A `Localhost` profile is a file **on the node**, in
`/var/lib/kubelet/seccomp/`: the Pods of this course are therefore placed on
`k8s-w1.lab` (`nodeName`).

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2 and containerd on Ubuntu 24.04.

Place two test profiles on `k8s-w1.lab`: `sans-mkdir.json`, which allows
everything except creating a directory, and `casse.json`, cut in the middle on
purpose:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo mkdir -p /var/lib/kubelet/seccomp/essai; echo "{\"defaultAction\":\"SCMP_ACT_ALLOW\",\"syscalls\":[{\"names\":[\"mkdir\",\"mkdirat\"],\"action\":\"SCMP_ACT_ERRNO\"}]}" | sudo tee /var/lib/kubelet/seccomp/essai/sans-mkdir.json; echo "{\"defaultAction\": \"SCMP_ACT_ALLOW\"," | sudo tee /var/lib/kubelet/seccomp/essai/casse.json'
```

```text
{"defaultAction":"SCMP_ACT_ALLOW","syscalls":[{"names":["mkdir","mkdirat"],"action":"SCMP_ACT_ERRNO"}]}
{"defaultAction": "SCMP_ACT_ALLOW",
```

## ✂️ Exercise 1: refuse a single family of calls

The lesson starts from an allow-list (`defaultAction: SCMP_ACT_ERRNO`) that
refuses everything not listed. The `sans-mkdir.json` profile does the
opposite: `defaultAction: SCMP_ACT_ALLOW`, and only `mkdir` and `mkdirat` are
refused. Start a Pod under this profile, then try to create a directory and a
file:

```bash
kubectl create namespace essai-seccomp; kubectl run sans-mkdir --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-seccomp --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"seccompProfile":{"type":"Localhost","localhostProfile":"essai/sans-mkdir.json"}}}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sans-mkdir -n essai-seccomp --timeout=60s; kubectl exec sans-mkdir -n essai-seccomp -- sh -c 'mkdir /tmp/rep; echo mkdir : code $?; touch /tmp/fichier; echo touch : code $?; grep Seccomp: /proc/1/status'
```

```text
namespace/essai-seccomp created
pod/sans-mkdir created
pod/sans-mkdir condition met
mkdir: can't create directory '/tmp/rep': Operation not permitted
mkdir : code 1
touch : code 0
Seccomp:	2
```

`mkdir` fails with `Operation not permitted`: that is the `EPERM` error
`SCMP_ACT_ERRNO` returns. `touch` passes, because creating a file is not a
`mkdir` call. `Seccomp: 2` confirms a filter is active. A deny-list like this
one goes in without breaking the application, but it only blocks what you
thought of listing.

## 🧩 Exercise 2: an unreadable profile

Now point to the `casse.json` profile, whose JSON is incomplete:

```bash
kubectl run casse --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-seccomp --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"seccompProfile":{"type":"Localhost","localhostProfile":"essai/casse.json"}}}}' -- sleep 3600; sleep 10; kubectl get pod casse -n essai-seccomp; kubectl get pod casse -n essai-seccomp -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-200
```

```text
pod/casse created
NAME    READY   STATUS                 RESTARTS   AGE
casse   0/1     CreateContainerError   0          11s
failed to create containerd container: decoding seccomp profile failed "/var/lib/kubelet/seccomp/essai/casse.json": unexpected end of JSON input
```

The API server accepts the Pod, then the container stays in
`CreateContainerError`. The message comes from containerd, on the node: it
names the file and the parsing error (`unexpected end of JSON input`). Before
pointing to a profile, check the file itself, for example with
`python3 -m json.tool` on the node.

## 🚦 Exercise 3: an init container confined on its own

A `securityContext` set on a container only applies to that container. Start a
Pod where only the init container `preparer` runs under `sans-mkdir.json`, and
the `app` container has no profile:

```bash
kubectl run init-confine --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-seccomp --overrides='{"spec":{"nodeName":"k8s-w1.lab","initContainers":[{"name":"preparer","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","mkdir /tmp/rep || echo mkdir refusé pour preparer"],"securityContext":{"seccompProfile":{"type":"Localhost","localhostProfile":"essai/sans-mkdir.json"}}}],"containers":[{"name":"app","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","mkdir /tmp/rep && echo mkdir permis pour app; sleep 3600"]}]}}' -- true; kubectl wait --for=condition=Ready pod/init-confine -n essai-seccomp --timeout=60s; kubectl logs init-confine -n essai-seccomp -c preparer; kubectl logs init-confine -n essai-seccomp -c app
```

```text
pod/init-confine created
pod/init-confine condition met
mkdir: can't create directory '/tmp/rep': Operation not permitted
mkdir refusé pour preparer
mkdir permis pour app
```

The logs of both containers show it: `mkdir` is refused in `preparer`,
allowed in `app`. Confining an init container does not protect the container
that runs afterwards. To cover the whole Pod, declare the profile in the
`securityContext` of the Pod, and every container inherits it.

## 🧹 Clean-up

Delete the test namespace, then the test profiles from `k8s-w1.lab`:

```bash
kubectl delete namespace essai-seccomp; ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo rm -rf /var/lib/kubelet/seccomp/essai'
```

```text
namespace "essai-seccomp" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-seccomp-profile
dsoxlab check cks-seccomp-profile
```

```text
╭─── Result: cks-seccomp-profile ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests  │
╰───────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a profile to place and a Pod to confine,
with the proof that the targeted call is refused and that an unconfined
witness still runs it.

```bash
dsoxlab run cks-seccomp-profile
dsoxlab challenge cks-seccomp-profile
```
