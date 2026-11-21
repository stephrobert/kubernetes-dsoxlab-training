# Label a node, show its role and reserve it for one team

The lesson shows how to manage nodes: labels, roles, `cordon` and taints. This
course adds cases the lesson does not show: a node with two roles, several
nodes labeled at once with a selector, an annotation you cannot select, a
value the API refuses, and an existing label that is not replaced unless you
ask.

You work on `k8s-w1.lab`, with labels that start with `essai` ("trial"). The
challenge is about another node: you will do it on your own, at the end.

Related page (in French): [Gérer les nœuds Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/gerer-noeuds-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-etiqueter-et-isoler-un-noeud
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🏷️ Exercise 1: two roles for one node

The `ROLES` column of `kubectl get nodes` is not a separate field: it lists
the labels whose key starts with `node-role.kubernetes.io/`. Put two of them on
`k8s-w1.lab` (`etagere` means "shelf"):

```bash
kubectl label node k8s-w1.lab node-role.kubernetes.io/essai= node-role.kubernetes.io/etagere=; kubectl get nodes
```

```text
node/k8s-w1.lab labeled
NAME         STATUS   ROLES           AGE     VERSION
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2
k8s-w1.lab   Ready    essai,etagere   6h26m   v1.37.2
k8s-w2.lab   Ready    <none>          87s     v1.37.2
```

Both roles show up, separated by a comma. A role has no effect on where Pods
are placed: it is a label like any other.

## 📦 Exercise 2: label several nodes at once

`kubectl label` accepts a selector instead of a name. Label every node that is
not the control plane, and show the value as a column (`salle` means "room"):

```bash
kubectl label nodes -l '!node-role.kubernetes.io/control-plane' essai-salle=b; kubectl get nodes -L essai-salle
```

```text
node/k8s-w1.lab labeled
node/k8s-w2.lab labeled
NAME         STATUS   ROLES           AGE     VERSION   ESSAI-SALLE
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2   
k8s-w1.lab   Ready    essai,etagere   6h26m   v1.37.2   b
k8s-w2.lab   Ready    <none>          87s     v1.37.2   b
```

The `!` before the key means "that does not carry this label". Both workers
got `essai-salle=b` in a single command.

## 📝 Exercise 3: an annotation cannot be selected

An annotation carries information for people or tools, such as a contact. Put
one, then try to search for it as a label:

```bash
kubectl annotate node k8s-w1.lab essai-contact=atelier@formation.test; kubectl get nodes -l essai-contact=atelier@formation.test
```

```text
node/k8s-w1.lab annotated
Error from server (BadRequest): Unable to find "/v1, Resource=nodes" that match label selector "essai-contact=atelier@formation.test", field selector "": unable to parse requirement: values[0][essai-contact]: Invalid value: "atelier@formation.test": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345', regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
```

The annotation is set, but the search fails: `-l` only reads labels, and an
address with `@` is not even a valid label value. To find the nodes that carry
an annotation, filter the output with a jsonpath:

```bash
kubectl get nodes -o jsonpath='{range .items[?(@.metadata.annotations.essai-contact)]}{.metadata.name}{"\n"}{end}'
```

```text
k8s-w1.lab
```

## 🚫 Exercise 4: a value the API refuses

A label value may only contain letters, digits, `-`, `_` and `.`. Try a value
with a space:

```bash
kubectl label node k8s-w1.lab essai-salle='salle b'
```

```text
error: invalid label value: "essai-salle=salle b": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345', regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
```

Refused, with the exact regular expression the value must match.

## ✏️ Exercise 5: change an existing value

`k8s-w1.lab` already carries `essai-salle=b`. Try to change it to `c`:

```bash
kubectl label node k8s-w1.lab essai-salle=c
```

```text
error: 'essai-salle' already has a value (b), and --overwrite is false
```

kubectl refuses to overwrite a value unless you ask. With `--overwrite`:

```bash
kubectl label node k8s-w1.lab essai-salle=c --overwrite; kubectl get nodes -L essai-salle
```

```text
node/k8s-w1.lab labeled
NAME         STATUS   ROLES           AGE     VERSION   ESSAI-SALLE
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2   
k8s-w1.lab   Ready    essai,etagere   6h26m   v1.37.2   c
k8s-w2.lab   Ready    <none>          88s     v1.37.2   b
```

Only `k8s-w1.lab` changed. This protection avoids overwriting by mistake a
label set by another tool or another team.

## 🧹 Clean-up

Remove the trial labels and annotation. A `-` after the key removes the label:

```bash
kubectl label nodes --all essai-salle- node-role.kubernetes.io/essai- node-role.kubernetes.io/etagere- 2>&1 | grep -v 'not found'; kubectl annotate node k8s-w1.lab essai-contact-; kubectl get nodes
```

```text
node/k8s-cp.lab not labeled
node/k8s-w1.lab unlabeled
node/k8s-w2.lab unlabeled
node/k8s-w1.lab annotated
NAME         STATUS   ROLES           AGE     VERSION
k8s-cp.lab   Ready    control-plane   6h33m   v1.37.2
k8s-w1.lab   Ready    <none>          6h26m   v1.37.2
k8s-w2.lab   Ready    <none>          88s     v1.37.2
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-etiqueter-et-isoler-un-noeud
dsoxlab check cka-etiqueter-et-isoler-un-noeud
```

```text
╭─ Result: cka-etiqueter-et-isoler-un-noeud ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests           │
╰────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a node to label, to show with its role, then
to reserve for one team.

```bash
dsoxlab run cka-etiqueter-et-isoler-un-noeud
dsoxlab challenge cka-etiqueter-et-isoler-un-noeud
```
