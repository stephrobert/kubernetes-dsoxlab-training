# Observe a sensitive file being read with Tetragon, then block it

The lesson compares Falco and Tetragon on the same scenario: reading a
sensitive file. Tetragon observes it, then blocks it with a `TracingPolicy`.
This course adds cases the lesson does not show: a file mounted in a Pod, that
Tetragon does not see under the name you expect; the difference between
upcoming events and the history; and the event a blocking leaves behind.

You work in a scratch namespace, `essai-tg`, with a `curieux` ("curious") Pod
that mounts a ConfigMap at `/etc/essai/`. The challenge is about other
objects: you will do it on your own, at the end.

Related page (in French): [Falco vs Tetragon : comparés sur le même cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/falco-vs-tetragon/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-observer-et-bloquer-avec-tetragon
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The lab's preparation
installed Tetragon, with one agent per node.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and Tetragon 1.8.0. The lesson shows 1.7.1:
policies are written the same way.

Create the trial Pod and its ConfigMap (`reglages` means "settings",
`niveau` "level"):

```bash
kubectl create namespace essai-tg; kubectl -n essai-tg create configmap reglages --from-literal=niveau=debug; kubectl -n essai-tg run curieux --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"containers":[{"name":"curieux","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","infinity"],"volumeMounts":[{"name":"r","mountPath":"/etc/essai"}]}],"volumes":[{"name":"r","configMap":{"name":"reglages"}}]}}'; kubectl -n essai-tg wait --for=condition=Ready pod/curieux --timeout=120s
```

```text
namespace/essai-tg created
configmap/reglages created
pod/curieux created
pod/curieux condition met
```

The exercises' commands find the Tetragon agent of the node where `curieux`
runs (an agent only sees its node), read its JSON events in the
`export-stdout` container, and only show those of `curieux`.

## 🙈 Exercise 1: Equal does not see a mounted file

Set a policy that observes the opening of `/etc/essai/niveau`, with the
lesson's `Equal` operator, read the file, then count the events:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: essai-egal
spec:
  kprobes:
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        - matchArgs:
            - index: 0
              operator: Equal
              values:
                - /etc/essai/niveau
YAML
sleep 5; kubectl -n essai-tg exec curieux -- cat /etc/essai/niveau; echo; sleep 5; AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system logs $AG -c export-stdout --since=20s | python3 -c 'import json,sys
for l in sys.stdin:
    e = json.loads(l).get("process_kprobe")
    if e and e["process"].get("pod", {}).get("name") == "curieux":
        print(e["policy_name"], e["action"], e["process"]["binary"], [a.get("file_arg", {}).get("path") for a in e["args"]])' | wc -l
```

```text
tracingpolicy.cilium.io/essai-egal created
debug
0
```

The file is read, but Tetragon reports **no** event. Look at how Kubernetes
mounts a ConfigMap:

```bash
kubectl -n essai-tg exec curieux -- ls -la /etc/essai/ | tail -3
```

```text
drwxr-xr-x    2 root     root          4096 Nov 21 18:48 ..2026_11_21_18_48_46.1301310973
lrwxrwxrwx    1 root     root            32 Nov 21 18:48 ..data -> ..2026_11_21_18_48_46.1301310973
lrwxrwxrwx    1 root     root            13 Nov 21 18:48 niveau -> ..data/niveau
```

`niveau` is a link to `..data/niveau`, itself a link to a timestamped
directory. The kernel opens the **real** file, at the end of the chain. The
path you see is therefore never the one Tetragon compares: an `Equal` on a
file mounted from a ConfigMap or a Secret never matches.

## 🎯 Exercise 2: Prefix sees the real path

Replace the policy with another one, that targets everything starting with
`/etc/essai/`:

```bash
kubectl delete tracingpolicy essai-egal; cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: essai-prefixe
spec:
  kprobes:
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/essai/
YAML
sleep 5; kubectl -n essai-tg exec curieux -- cat /etc/essai/niveau; echo; sleep 5; AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system logs $AG -c export-stdout --since=20s | python3 -c 'import json,sys
for l in sys.stdin:
    e = json.loads(l).get("process_kprobe")
    if e and e["process"].get("pod", {}).get("name") == "curieux":
        print(e["policy_name"], e["action"], e["process"]["binary"], [a.get("file_arg", {}).get("path") for a in e["args"]])'
```

```text
tracingpolicy.cilium.io "essai-egal" deleted
tracingpolicy.cilium.io/essai-prefixe created
debug
essai-prefixe KPROBE_ACTION_POST /bin/cat ['/etc/essai/..2026_11_21_18_48_46.1301310973/niveau']
```

This time, the event arrives: the policy, the action (`KPROBE_ACTION_POST`, an
observation only), the binary, and the real path of the file, with its
timestamped directory. `Prefix` covers the mounted directory, whatever the
name of the hidden directory.

## 📡 Exercise 3: tetra getevents only sees the future

`tetra getevents` queries the agent live. Run it on `curieux` for 10 seconds,
without doing anything in the Pod:

```bash
AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system exec $AG -c tetragon -- timeout 10 tetra getevents -o compact --pods curieux | wc -l
```

```text
0
```

Zero lines: the read of exercise 2 is already past, and `tetra getevents` only
shows what happens while it listens. Run it again, with a read done during the
listening. The `sed` removes the pictograms at the start of the lines:

```bash
AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); (sleep 4; kubectl -n essai-tg exec curieux -- head -c 3 /etc/essai/niveau > /dev/null) & kubectl -n kube-system exec $AG -c tetragon -- timeout 12 tetra getevents -o compact --pods curieux 2>&1 | grep -E 'head|security_file_open' | sed 's/^[^a-z]*//' | cut -c1-120
```

```text
process essai-tg/curieux /bin/head "-c 3 /etc/essai/niveau"
syscall essai-tg/curieux /bin/head security_file_open
exit    essai-tg/curieux /bin/head "-c 3 /etc/essai/niveau" 0
```

The start of `head`, the file opening spotted by the policy, then the end of
the process. To read the past again, the `export-stdout` logs are what you
read, as in exercises 1 and 2.

## 🛑 Exercise 4: the event of a blocking

Add the `Sigkill` action to the same policy, and read the file again
(`bloque` means "blocks"):

```bash
kubectl delete tracingpolicy essai-prefixe; cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: essai-bloque
spec:
  kprobes:
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/essai/
          matchActions:
            - action: Sigkill
YAML
sleep 5; kubectl -n essai-tg exec curieux -- cat /etc/essai/niveau; echo "code : $?"; sleep 5; AG=$(kubectl -n kube-system get pods -l app.kubernetes.io/name=tetragon --field-selector spec.nodeName=$(kubectl -n essai-tg get pod curieux -o jsonpath='{.spec.nodeName}') -o jsonpath='{.items[0].metadata.name}'); kubectl -n kube-system logs $AG -c export-stdout --since=20s | python3 -c 'import json,sys
for l in sys.stdin:
    e = json.loads(l).get("process_kprobe")
    if e and e["process"].get("pod", {}).get("name") == "curieux":
        print(e["policy_name"], e["action"], e["process"]["binary"], [a.get("file_arg", {}).get("path") for a in e["args"]])'
```

```text
tracingpolicy.cilium.io "essai-prefixe" deleted
tracingpolicy.cilium.io/essai-bloque created
command terminated with exit code 137
code : 137
essai-prefixe KPROBE_ACTION_POST /bin/head ['/etc/essai/..2026_11_21_18_48_46.1301310973/niveau']
essai-bloque KPROBE_ACTION_SIGKILL /bin/cat ['/etc/essai/..2026_11_21_18_48_46.1301310973/niveau']
```

The process is killed (code 137), before reading the file. The event says so:
action `KPROBE_ACTION_SIGKILL`, with the binary and the targeted file. The line
before, an observation from exercise 3, comes from the window of the last 20
seconds: a blocking leaves the same trace as an observation, with another
action.

## 🧹 Clean-up

Remove the trial policy and the namespace. A forgotten `TracingPolicy` would
keep killing processes:

```bash
kubectl delete tracingpolicy essai-bloque; kubectl delete namespace essai-tg; kubectl get tracingpolicies
```

```text
tracingpolicy.cilium.io "essai-bloque" deleted
namespace "essai-tg" deleted
No resources found
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-observer-et-bloquer-avec-tetragon
dsoxlab check k8s-observer-et-bloquer-avec-tetragon
```

```text
╭─ Result: k8s-observer-et-bloquer-avec-tetragon ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                │
╰─────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an API key mounted from a Secret, read on
the sly by one of two Pods. Find which one and with which tool, then block any
read of the key, and nothing else.

```bash
dsoxlab run k8s-observer-et-bloquer-avec-tetragon
dsoxlab challenge k8s-observer-et-bloquer-avec-tetragon
```
