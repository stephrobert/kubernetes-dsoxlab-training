# Harden a Pod with a securityContext

The lesson shows the `securityContext`: a container's user, forbidding
privilege escalation, a read-only root, dropped capabilities. This course
focuses on identity and escalation, and adds cases the lesson does not show:
`runAsNonRoot` against an image that runs as root, `runAsUser` overriding the
image, a combination the API refuses, and the proof read from the kernel,
through `/proc/1/status`.

You work in a scratch namespace, `essai-identite` ("test-identity"), with
scratch Pods. The challenge is about another Pod: you will do it on your own,
at the end.

Related page: [Security Context](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/security-context/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-security-context-hardened
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🚫 Exercise 1: runAsNonRoot against an image that runs as root

`runAsNonRoot: true` asks the kubelet to refuse to start a container that
would run as root. Create the namespace and a Pod with the agnhost image,
which declares no user and therefore runs as root:

```bash
kubectl create namespace essai-identite; kubectl run nomme --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-identite --overrides='{"spec":{"securityContext":{"runAsNonRoot":true}}}' -- pause; sleep 10; kubectl get pod nomme -n essai-identite
```

```text
namespace/essai-identite created
pod/nomme created
NAME    READY   STATUS                       RESTARTS   AGE
nomme   0/1     CreateContainerConfigError   0          10s
```

The Pod stays in `CreateContainerConfigError`. Read the message:

```bash
kubectl get pod nomme -n essai-identite -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```text
container has runAsNonRoot and image will run as root (pod: "nomme_essai-identite(3c670f91-dd43-41c2-b343-b0cceaf4b224)", container: nomme)
```

The kubelet checked the user the image would use, and refused. `runAsNonRoot`
does not change the user: it only prevents starting as root. It is a
safeguard, not a fix.

## 🆔 Exercise 2: set the identity in the Pod

Keep `runAsNonRoot`, and add `runAsUser` and `runAsGroup` at Pod level:

```bash
kubectl run chiffre --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-identite --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":4242,"runAsGroup":4242}}}' -- pause; kubectl wait --for=condition=Ready pod/chiffre -n essai-identite --timeout=120s; kubectl exec chiffre -n essai-identite -- id
```

```text
pod/chiffre created
pod/chiffre condition met
uid=4242 gid=4242 groups=4242
```

The Pod runs, as user and group 4242. `runAsUser` overrides what the image
plans, and `runAsNonRoot` is satisfied since 4242 is not 0. The user does not
need to exist in the image: the kernel only knows numbers.

## ⛔ Exercise 3: a combination the API refuses

Create a container that is both `privileged: true` and
`allowPrivilegeEscalation: false`:

```bash
kubectl run contradiction --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-identite --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"privileged":true,"allowPrivilegeEscalation":false}}]}}' -- sleep 3600
```

```text
The Pod "contradiction" is invalid: spec.containers[0].securityContext: Invalid value: {"Capabilities":null,"Privileged":true,"SELinuxOptions":null,"WindowsOptions":null,"RunAsUser":null,"RunAsGroup":null,"RunAsNonRoot":null,"ReadOnlyRootFilesystem":null,"AllowPrivilegeEscalation":false,"ProcMount":null,"SeccompProfile":null,"AppArmorProfile":null}: cannot set `allowPrivilegeEscalation` to false and `privileged` to true
```

The API refuses the Pod. The end of the message gives the reason: a
privileged container already has every right, so forbidding escalation makes
no sense. The API would rather refuse a contradictory configuration than
ignore part of it.

## 🔬 Exercise 4: read the proof in /proc

The `securityContext` describes an intention. The kernel says what really
applies. Create a Pod with `runAsUser: 2000`,
`allowPrivilegeEscalation: false` and every capability dropped, then read the
main process's state:

```bash
kubectl run temoin --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-identite --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"runAsUser":2000,"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/temoin -n essai-identite --timeout=120s; kubectl exec temoin -n essai-identite -- grep -E '^(Uid|Gid|NoNewPrivs|CapEff|CapBnd)' /proc/1/status
```

```text
pod/temoin created
pod/temoin condition met
Uid:	2000	2000	2000	2000
Gid:	0	0	0	0
CapEff:	0000000000000000
CapBnd:	0000000000000000
NoNewPrivs:	1
```

`Uid` is 2000. `Gid` is 0: without `runAsGroup`, the group stays the image's,
here root. `CapEff` and `CapBnd` at zero: no capability, neither active nor
recoverable. `NoNewPrivs: 1` is the translation of
`allowPrivilegeEscalation: false`: the process can never gain rights, not even
through a setuid program. Compare with a Pod without any `securityContext`:

```bash
kubectl run ordinaire --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-identite -- sleep 3600; kubectl wait --for=condition=Ready pod/ordinaire -n essai-identite --timeout=120s; kubectl exec ordinaire -n essai-identite -- grep -E '^(Uid|NoNewPrivs|CapEff)' /proc/1/status
```

```text
pod/ordinaire created
pod/ordinaire condition met
Uid:	0	0	0	0
CapEff:	00000000a80425fb
NoNewPrivs:	0
```

Root, with the runtime's default capabilities (`a80425fb`), and escalation
allowed. That is the starting state of any Pod that asks for nothing.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-identite
```

```text
namespace "essai-identite" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-security-context-hardened
dsoxlab check ckad-security-context-hardened
```

```text
╭─ Result: ckad-security-context-hardened ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests         │
╰──────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a web server to harden, which must keep
answering.

```bash
dsoxlab run ckad-security-context-hardened
dsoxlab challenge ckad-security-context-hardened
```
