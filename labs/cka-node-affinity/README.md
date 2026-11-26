# Placing with nodeAffinity: required constraint and preference

The lesson shows `nodeAffinity`: a required constraint that picks the possible
nodes, and a preference that ranks them. This course adds cases the lesson
does not show: the difference between AND and OR depending on where you write
a condition, comparing a number with `Gt`, naming a node with `matchFields`,
two preferences with different weights, and a label removed after placement.

You work in a scratch namespace, `essai-affinite`, with two scratch labels set
on the nodes: `essai-zone` and `essai-generation`. The challenge is about
other labels and other objects: you will do it on your own, at the end.

Related page: [Affinity, tolerations and taints](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/affinity-tolerations-and-taints/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-node-affinity
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and set the scratch labels: the control plane is in zone
`nord` ("north"), generation 3, the worker in zone `sud` ("south"),
generation 5.

```bash
kubectl create namespace essai-affinite; kubectl label node k8s-cp.lab essai-zone=nord essai-generation=3; kubectl label node k8s-w1.lab essai-zone=sud essai-generation=5; kubectl get nodes -L essai-zone,essai-generation
```

```text
namespace/essai-affinite created
node/k8s-cp.lab labeled
node/k8s-w1.lab labeled
NAME         STATUS   ROLES           AGE   VERSION   ESSAI-ZONE   ESSAI-GENERATION
k8s-cp.lab   Ready    control-plane   35h   v1.37.2   nord         3
k8s-w1.lab   Ready    <none>          35h   v1.37.2   sud          5
```

Every Pod in this course tolerates the control plane's taint: without it, the
control plane would always be excluded, and the exercises would only see one
node. The command creates the Pod, waits 6 seconds, then shows its name, its
state and its node.

## 🔀 Exercise 1: AND inside a term, OR between two terms

Create a Pod with a single term (`nodeSelectorTerms`) holding two conditions:
zone `nord` and generation 5.

```bash
kubectl run et --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["nord"]},{"key":"essai-generation","operator":"In","values":["5"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod et -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
et    Pending   <none>
```

Create the same Pod with two separate terms, one condition each:

```bash
kubectl run ou --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["nord"]}]},{"matchExpressions":[{"key":"essai-generation","operator":"In","values":["5"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod ou -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
ou    Running   k8s-w1.lab
```

The first one stays `Pending`, the second runs on the worker. Inside one term,
every condition must be true (AND): no node is both `nord` and generation 5.
Between two terms, one is enough (OR): the worker is generation 5. The
scheduler explains why it refused the first one:

```bash
kubectl get events -n essai-affinite --field-selector involvedObject.name=et,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/2 nodes are available: 2 node(s) didn't match Pod's node affinity/selector. preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

## 🔢 Exercise 2: compare a number with Gt

The `Gt` operator compares a label with a number. Ask for a generation greater
than 4:

```bash
kubectl run recent --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-generation","operator":"Gt","values":["4"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod recent -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
recent   Running   k8s-w1.lab
```

The Pod goes to the worker, generation 5. The label's value is text, but `Gt`
and `Lt` read it as an integer.

## 🎯 Exercise 3: name a node with matchFields

`matchFields` compares a field of the Node object, not a label. Only
`metadata.name` is accepted:

```bash
kubectl run nomme --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchFields":[{"key":"metadata.name","operator":"In","values":["k8s-cp.lab"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod nomme -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
nomme   Running   k8s-cp.lab
```

The Pod is on `k8s-cp.lab`, named explicitly. Unlike `nodeName`, which places
the Pod without going through the scheduler, `matchFields` goes through it:
resources and taints are checked.

## ⚖️ Exercise 4: two preferences, two weights

Create three Pods with two preferences: zone `nord` with a weight of 10, zone
`sud` with a weight of 90.

```bash
for i in 1 2 3; do kubectl run prefere-$i --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"preferredDuringSchedulingIgnoredDuringExecution":[{"weight":10,"preference":{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["nord"]}]}},{"weight":90,"preference":{"matchExpressions":[{"key":"essai-zone","operator":"In","values":["sud"]}]}}]}}}}' -- sleep 3600 >/dev/null; done; sleep 6; kubectl get pods -n essai-affinite -l run -o custom-columns=NOM:.metadata.name,NOEUD:.spec.nodeName --no-headers | grep prefere
```

```text
prefere-1   k8s-w1.lab
prefere-2   k8s-w1.lab
prefere-3   k8s-w1.lab
```

All three Pods go to the worker, in zone `sud`. The scheduler adds the weight
of each satisfied preference to the node's score, and 90 beats 10. A
preference forbids nothing: if the worker were full, the Pods would go to the
control plane.

## 🏷️ Exercise 5: remove the label after placement

Remove the `essai-generation` label from the worker (the final `-` deletes
it), and look at the `recent` Pod, placed in exercise 2 thanks to it:

```bash
kubectl label node k8s-w1.lab essai-generation-; sleep 10; kubectl get pod recent -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab unlabeled
recent   Running   k8s-w1.lab
```

The Pod still runs on the worker. The end of the name
`requiredDuringSchedulingIgnoredDuringExecution` says it: the rule counts at
placement, and is ignored afterwards. Recreate the Pod:

```bash
kubectl delete pod recent -n essai-affinite; kubectl run recent --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-affinite --overrides='{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}],"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"essai-generation","operator":"Gt","values":["4"]}]}]}}}}}' -- sleep 3600 >/dev/null; sleep 6; kubectl get pod recent -n essai-affinite -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod "recent" deleted from essai-affinite namespace
recent   Pending   <none>
```

This time it stays `Pending`: no node carries a generation any more. A removed
label moves nothing, but it blocks the next placement, for example when a
Deployment recreates the Pod.

## 🧹 Clean-up

Delete the namespace and remove the scratch labels from both nodes. The
`label "essai-generation" not found` warning comes from the worker, whose
label was already removed in exercise 5:

```bash
kubectl delete namespace essai-affinite; kubectl label node k8s-cp.lab essai-zone- essai-generation-; kubectl label node k8s-w1.lab essai-zone- essai-generation-; kubectl get nodes -L essai-zone,essai-generation
```

```text
namespace "essai-affinite" deleted
node/k8s-cp.lab unlabeled
label "essai-generation" not found.
node/k8s-w1.lab unlabeled
NAME         STATUS   ROLES           AGE   VERSION   ESSAI-ZONE   ESSAI-GENERATION
k8s-cp.lab   Ready    control-plane   35h   v1.37.2                
k8s-w1.lab   Ready    <none>          35h   v1.37.2                
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-node-affinity
dsoxlab check cka-node-affinity
```

```text
╭──── Result: cka-node-affinity ────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: applications to place with constraints and
preferences on node labels.

```bash
dsoxlab run cka-node-affinity
dsoxlab challenge cka-node-affinity
```
