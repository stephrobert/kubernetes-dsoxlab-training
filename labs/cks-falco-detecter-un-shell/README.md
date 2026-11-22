# Write a Falco rule that detects a specific move

The lesson shows how Falco watches system calls, how a rule reads, and how to
add one. This course adds three moves it does not show: finding the exact name
of a field, getting a faulty rule refused **before** restarting Falco, and
reading an alert field by field.

You work with a test rule that spots the creation of a `/tmp/marque*` file in
the `essai-falco` namespace. The challenge targets another rule and other
namespaces: you will do it on your own, at the end.

Related page: [Falco](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/falco/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-falco-detecter-un-shell
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Falco runs there, installed from its package, and writes
its alerts as JSON to `/var/log/falco/events.json`.

The outputs shown in this course were recorded on this machine on
22 November 2026.

## 🔎 Exercise 1: the exact name of a field

A rule filters on **fields**: the opened file, the Pod, the namespace… An
approximate name makes the rule fail. `falco --list` gives the full list, with
a description:

```bash
sudo falco --list 2>/dev/null | grep -E '^k8s\.(ns|pod)\.name|^container\.name|^fd\.name ' | cut -c1-110
```

```text
fd.name                       FD full name. If the fd is a file, this field contains the full path. If the FD 
container.name                The container name. In instances of userspace container engine lookup delays, th
k8s.pod.name                  The Kubernetes pod name. This field is extracted from the container runtime sock
k8s.ns.name                   The Kubernetes namespace name. This field is extracted from the container runtim
```

The namespace is spelled `k8s.ns.name`, not `k8s.namespace.name` as you would
write it from memory. These fields come from the container runtime of the
node: Falco reads them without querying the API server.

## ✅ Exercise 2: a rule refused before the restart

A Falco that restarts on a faulty rule refuses to start, and nothing is
watched any more. `falco -V` validates rule files without loading anything.
Write a rule that uses the wrong field name, and validate it alone:

```bash
cat > /tmp/essai.yaml <<'YAML'
- rule: Essai marque dans tmp
  desc: un fichier marque est créé dans /tmp d'un conteneur du namespace essai-falco
  condition: open_write and container and k8s.namespace.name = essai-falco and fd.name startswith /tmp/marque
  output: marque écrite (fichier=%fd.name ns=%k8s.ns.name pod=%k8s.pod.name cmd=%proc.cmdline)
  priority: NOTICE
YAML
sudo falco -V /tmp/essai.yaml 2>&1 | grep -oE 'LOAD_ERR_[A-Z]+ [^.]*\.' | head -2
```

```text
LOAD_ERR_VALIDATE (Error validating rule/macro/list/exception objects): Undefined macro 'open_write' used in filter.
```

Falco does not report the field, but the `open_write` macro, unknown. It is
defined in the provided rules, which you did not pass to the validation.
Validate your file **with** the provided rules, in the order Falco loads them:

```bash
sudo falco -V /etc/falco/falco_rules.yaml -V /tmp/essai.yaml 2>&1 | grep -E '^\.\.\.|^ +\^|^LOAD_ERR'; echo "validation : code ${PIPESTATUS[0]}"
```

```text
...tainer and k8s.namespace.name = essai-falco and fd.name startswith /tmp/marque
                                                                                ^
LOAD_ERR_COMPILE_CONDITION (Error compiling condition): filter_check called with nonexistent field k8s.namespace.name
validation : code 1
```

This time, the real fault: the `^` marker points at the end of the condition,
and the last line names the field that does not exist. Code 1. Fix the field
and validate again:

```bash
cat > /tmp/essai.yaml <<'YAML'
- rule: Essai marque dans tmp
  desc: un fichier marque est créé dans /tmp d'un conteneur du namespace essai-falco
  condition: open_write and container and k8s.ns.name = essai-falco and fd.name startswith /tmp/marque
  output: marque écrite (fichier=%fd.name ns=%k8s.ns.name pod=%k8s.pod.name cmd=%proc.cmdline)
  priority: NOTICE
YAML
sudo falco -V /etc/falco/falco_rules.yaml -V /tmp/essai.yaml 2>&1 | tail -1 | jq -c '[.falco_load_results[] | {name, successful}]'
```

```text
[{"name":"/etc/falco/falco_rules.yaml","successful":true},{"name":"/tmp/essai.yaml","successful":true}]
```

Both files are accepted: you can restart safely.

## 🚨 Exercise 3: load the rule, trigger it, read the alert

Install the rule in `/etc/falco/rules.d/`, which Falco reads at startup, and
restart the service:

```bash
sudo install -m 0644 /tmp/essai.yaml /etc/falco/rules.d/essai.yaml; sudo systemctl restart falco-modern-bpf; sleep 15; systemctl is-active falco-modern-bpf
```

```text
active
```

Start a test Pod on `k8s-cp.lab`, where Falco watches, and create a marker
file in it:

```bash
kubectl create namespace essai-falco; kubectl run marqueur -n essai-falco --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --overrides='{"spec":{"nodeName":"k8s-cp.lab","tolerations":[{"operator":"Exists"}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/marqueur -n essai-falco --timeout=90s; kubectl exec marqueur -n essai-falco -- touch /tmp/marque-1; sleep 5
```

```text
namespace/essai-falco created
pod/marqueur created
pod/marqueur condition met
```

Each alert is one JSON line. `jq` extracts its priority, its rule and the
fields used in the message:

```bash
sudo grep '"rule":"Essai marque dans tmp"' /var/log/falco/events.json | tail -1 | jq -c '{priority, rule, champs: .output_fields | {"fd.name", "k8s.ns.name", "k8s.pod.name", "proc.cmdline"}}'
```

```text
{"priority":"Notice","rule":"Essai marque dans tmp","champs":{"fd.name":"/tmp/marque-1","k8s.ns.name":"essai-falco","k8s.pod.name":"marqueur","proc.cmdline":"touch /tmp/marque-1"}}
```

Everything an investigation needs is there: the file, the namespace, the Pod
and the exact command. These fields, not the text of the message, are what an
alert collection tool should read.

## 🧹 Clean-up

Delete the test namespace, remove the rule, then restart Falco so it forgets
it:

```bash
kubectl delete namespace essai-falco --wait=true --timeout=120s; sudo rm -f /etc/falco/rules.d/essai.yaml /tmp/essai.yaml; sudo systemctl restart falco-modern-bpf; sleep 10; systemctl is-active falco-modern-bpf; ls /etc/falco/rules.d/
```

```text
namespace "essai-falco" deleted
active
```

Falco is active, and `rules.d/` is empty.

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-falco-detecter-un-shell
dsoxlab check cks-falco-detecter-un-shell
```

```text
╭─ Result: cks-falco-detecter-un-shell ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests      │
╰───────────────────────────────────────╯
```

That is the expected result on a fresh lab. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a rule that alerts as soon as a shell opens
in a sensitive namespace, and not in the others.

```bash
dsoxlab run cks-falco-detecter-un-shell
dsoxlab challenge cks-falco-detecter-un-shell
```
