# Enforce a security standard on the Pods of a namespace

The lesson shows the three levels of the Pod Security Standards and the three
modes that apply them to a namespace. This course adds three cases it does not
show: a Pod that `baseline` lets through and `restricted` refuses, a
Deployment accepted whose Pods are refused, and how to know what a level would
break **before** setting it.

You work in the `essai-psa` namespace. The challenge targets another namespace
and other Pods: you will do it on your own, at the end.

Related page: [Pod Security Standards](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-pod-security-admission
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2.

## 🪜 Exercise 1: baseline lets it through, restricted refuses

Create a namespace at the `baseline` level, and start an ordinary Pod in it,
running as root with no security setting at all:

```bash
kubectl create namespace essai-psa; kubectl label namespace essai-psa pod-security.kubernetes.io/enforce=baseline; kubectl run ouvert --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-psa -- sleep 3600
```

```text
namespace/essai-psa created
namespace/essai-psa labeled
pod/ouvert created
```

Accepted: `baseline` refuses dangerous moves (privileged Pod, access to the
host namespaces), not an ordinary container running as root. Now raise the
namespace to `restricted`, and start a second, identical Pod:

```bash
kubectl label namespace essai-psa pod-security.kubernetes.io/enforce=restricted --overwrite 2>&1; kubectl run ouvert-2 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-psa -- sleep 3600 2>&1 | cut -c1-220
```

```text
Warning: existing pods in namespace "essai-psa" violate the new PodSecurity enforce level "restricted:latest"
Warning: ouvert: allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile
namespace/essai-psa labeled
Error from server (Forbidden): pods "ouvert-2" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "ouvert-2" must set securityContext.allowPrivilegeEscalation=false), unr
```

Two things to read. The label is set, with a warning: the Pod `ouvert`,
already there, violates the new level, but it **keeps running**. Admission
only judges what arrives, never what exists. The second Pod is refused, and
the message lists every field at fault.

## 🏭 Exercise 2: a Deployment accepted, its Pods refused

Create a Deployment in this `restricted` namespace:

```bash
kubectl create deployment vitrine --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-psa -- sleep 3600; sleep 5; kubectl get deployment vitrine -n essai-psa
```

```text
Warning: would violate PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "busybox" must set securityContext.allowPrivilegeEscalation=false), unrestricted capabilities (container "busybox" must
deployment.apps/vitrine created
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   0/1     0            0           5s
```

The Deployment is created, with a mere warning, but it stays at `0/1`.
Admission does not refuse the Deployment: it is not a Pod. It refuses the Pods
its ReplicaSet tries to create. The error shows in the events of the
ReplicaSet:

```bash
kubectl describe replicaset -n essai-psa -l app=vitrine | sed -n '/Events:/,$p' | tail -1 | cut -c1-220
```

```text
  Warning  FailedCreate  2s    replicaset-controller  (combined from similar events): Error creating: pods "vitrine-84fc98bb46-r2hcf" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != fa
```

`FailedCreate`, with the same reason as for a Pod created by hand. When a
Deployment stays at 0 without any failing Pod, look at the ReplicaSet: that
is the symptom of a refusal at admission.

## 🔮 Exercise 3: what a level would break, before setting it

`--dry-run=server` has a change judged by the API server without saving it.
Applied to a level label, it lists the existing Pods that would be in
violation. Try it on `kube-system`, where you would never set `restricted`:

```bash
kubectl label --dry-run=server --overwrite namespace kube-system pod-security.kubernetes.io/enforce=restricted 2>&1 | cut -c1-160 | head -8
```

```text
Warning: existing pods in namespace "kube-system" violate the new PodSecurity enforce level "restricted:latest"
Warning: coredns-559f6c778d-bc5cl (and 1 other pod): runAsNonRoot != true, seccompProfile
Warning: etcd-k8s-cp.lab (and 3 other pods): host namespaces, hostPort, probe or lifecycle host, allowPrivilegeEscalation != false, unrestricted capabilities, r
Warning: kube-proxy-9fvg6 (and 2 other pods): host namespaces, privileged, allowPrivilegeEscalation != false, unrestricted capabilities, restricted volume types
namespace/kube-system labeled (server dry run)
```

Each line names a Pod and what would not pass: the control plane components
use the host namespaces, kube-proxy is privileged. The last line,
`(server dry run)`, says nothing was written. Check it:

```bash
kubectl get namespace kube-system -o jsonpath='{.metadata.labels}{"\n"}'
```

```text
{"kubernetes.io/metadata.name":"kube-system"}
```

No level label on `kube-system`. Run this simulation on each namespace before
fencing it, and you know in advance which Pods will need fixing.

Finally, a level can be **pinned** to the rules of a given Kubernetes version,
with the `enforce-version` label. The behaviour then stops changing when the
cluster is upgraded:

```bash
kubectl label namespace essai-psa pod-security.kubernetes.io/enforce-version=v1.36 --overwrite; kubectl get namespace essai-psa -o jsonpath='{.metadata.labels}{"\n"}'
```

```text
Warning: existing pods in namespace "essai-psa" violate the new PodSecurity enforce level "restricted:v1.36"
Warning: ouvert: allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile
namespace/essai-psa labeled
{"kubernetes.io/metadata.name":"essai-psa","pod-security.kubernetes.io/enforce":"restricted","pod-security.kubernetes.io/enforce-version":"v1.36"}
```

The warning now names `restricted:v1.36` instead of `restricted:latest`.
`latest` follows the rules of the cluster version, which may refuse tomorrow a
Pod accepted today.

## 🧹 Clean-up

Delete the test namespace, with the Pod and the Deployment it holds:

```bash
kubectl delete namespace essai-psa
```

```text
namespace "essai-psa" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-pod-security-admission
dsoxlab check cks-pod-security-admission
```

```text
╭─ Result: cks-pod-security-admission ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests     │
╰──────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a namespace to put under the `restricted`
standard in all three modes, and a Pod that must run in it while following
it.

```bash
dsoxlab run cks-pod-security-admission
dsoxlab challenge cks-pod-security-admission
```
