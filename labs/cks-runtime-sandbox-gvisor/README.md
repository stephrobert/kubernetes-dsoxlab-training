# Isolate a sensitive workload in a gVisor sandbox

The lesson shows how gVisor puts an application kernel between the container
and the machine, and how a RuntimeClass sends a Pod to it. This course adds
three cases it only mentions: a handler the node does not know and the event
that says so, the startup of the gVisor kernel seen from inside the Pod, and
the cost of the sandbox declared to the Pod through the `overhead` field.

You work in the `essai-sandbox` namespace, with two test RuntimeClasses. The
challenge targets another RuntimeClass and other Pods: you will do it on your
own, at the end.

Related page: [Runtime Sandboxes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-runtime-sandbox-gvisor
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). containerd knows a second runtime there, `runsc`, the
gVisor one. The Pods of this course are placed on `k8s-cp.lab` (`nodeName`),
the only node where it is installed.

The outputs shown in this course were recorded on this machine on
22 November 2026.

## 🧭 Exercise 1: a handler the node does not know

A RuntimeClass maps a name to a **handler**, the name of the runtime in the
containerd configuration. Nothing checks that name at creation time. Create a
RuntimeClass whose handler does not exist, and a Pod that uses it:

```bash
kubectl create namespace essai-sandbox; cat <<'YAML' | kubectl apply -f -
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: essai-faux
handler: runsc-absent
YAML
kubectl run mal-route -n essai-sandbox --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab","runtimeClassName":"essai-faux"}}' -- sleep 3600; sleep 15; kubectl get pod mal-route -n essai-sandbox
```

```text
namespace/essai-sandbox created
runtimeclass.node.k8s.io/essai-faux created
pod/mal-route created
NAME        READY   STATUS              RESTARTS   AGE
mal-route   0/1     ContainerCreating   0          15s
```

The API server accepts everything, and the Pod stays in `ContainerCreating`.
The reason is in the events of the Pod:

```bash
kubectl get events -n essai-sandbox --field-selector involvedObject.name=mal-route,reason=FailedCreatePodSandBox -o custom-columns=RAISON:.reason,MESSAGE:.message --no-headers | tail -1 | cut -c1-320
```

```text
FailedCreatePodSandBox   Failed to create pod sandbox: rpc error: code = Unknown desc = unable to get OCI runtime for sandbox "4e3edc2894634cbf25afd52893970c884fd50dd7ebcd5122b14d3badcc42ea44": no runtime for "runsc-absent" is configured
```

`no runtime for "runsc-absent" is configured`: containerd, on the node, does
not know that handler. A Pod stuck in `ContainerCreating` behind a
RuntimeClass is diagnosed there, not in the application logs.

## 🛡️ Exercise 2: the gVisor kernel, seen from inside

Create a test RuntimeClass pointing to the real `runsc` handler, with an
`overhead` field used in the next exercise. Start a Pod that uses it, and an
ordinary Pod:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: essai-bac
handler: runsc
overhead:
  podFixed:
    memory: 64Mi
    cpu: 100m
YAML
kubectl run bac -n essai-sandbox --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab","runtimeClassName":"essai-bac"}}' -- sleep 3600; kubectl run hote -n essai-sandbox --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/bac pod/hote -n essai-sandbox --timeout=120s
```

```text
runtimeclass.node.k8s.io/essai-bac created
pod/bac created
pod/hote created
pod/bac condition met
pod/hote condition met
```

Ask each one for the kernel boot log, with `dmesg`:

```bash
for p in hote bac; do echo "--- $p"; kubectl exec $p -n essai-sandbox -- dmesg 2>&1 | head -3; done
```

```text
--- hote
dmesg: klogctl: Operation not permitted
command terminated with exit code 1
--- bac
[   0.000000] Starting gVisor...
[   0.579025] Rewriting the kernel in Rust...
[   0.654146] Letting the watchdogs out...
```

The ordinary Pod is not allowed to read the kernel log of the machine. The
sandboxed Pod reads that of **its own** kernel: the gVisor Sentry, which
writes these whimsical lines at startup. Its system calls never reach the
kernel of the machine: the Sentry answers them.

## 💰 Exercise 3: the cost of the sandbox, declared to the Pod

A sandbox uses memory and CPU on top of the container. The `overhead` field
of the RuntimeClass declares it, and admission copies it into every Pod that
uses it. Compare the two Pods:

```bash
for p in hote bac; do printf '%-5s runtimeClass=%-10s overhead=%s\n' $p "$(kubectl get pod $p -n essai-sandbox -o jsonpath='{.spec.runtimeClassName}')" "$(kubectl get pod $p -n essai-sandbox -o jsonpath='{.spec.overhead}')"; done
```

```text
hote  runtimeClass=           overhead=
bac   runtimeClass=essai-bac  overhead={"cpu":"100m","memory":"64Mi"}
```

The sandboxed Pod carries `overhead`: 100m of CPU and 64Mi of memory, which
the scheduler adds to its requests to pick a node and which quotas count. The
ordinary Pod has none. Without this field, a node full of sandboxed Pods would
be overloaded by costs nobody declared.

## 🧹 Clean-up

Delete the test namespace, then both RuntimeClasses, which belong to no
namespace:

```bash
kubectl delete namespace essai-sandbox --wait=true --timeout=120s; kubectl delete runtimeclass essai-bac essai-faux
```

```text
namespace "essai-sandbox" deleted
runtimeclass.node.k8s.io "essai-bac" deleted
runtimeclass.node.k8s.io "essai-faux" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-runtime-sandbox-gvisor
dsoxlab check cks-runtime-sandbox-gvisor
```

```text
╭─ Result: cks-runtime-sandbox-gvisor ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests     │
╰──────────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: declare gVisor to the cluster and run a
sensitive Pod in it, with the proof that it does not see the kernel of the
machine.

```bash
dsoxlab run cks-runtime-sandbox-gvisor
dsoxlab challenge cks-runtime-sandbox-gvisor
```
