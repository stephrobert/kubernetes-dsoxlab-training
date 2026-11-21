# Reserve a node: taint, toleration and nodeSelector

The lesson shows a taint, which keeps Pods off a node, and a toleration, which
lets a Pod go there anyway. This course tries each taint effect on the worker
and adds cases the lesson does not show: the tolerations every Pod gets
without writing them, a taint that evicts nobody, a toleration aimed at the
wrong effect, a universal toleration, a taint that evicts, a taint that is
only a preference, and the taint that `kubectl cordon` sets.

You work in a scratch namespace, `essai-taint`, with a scratch taint,
`essai-maintenance=oui` ("maintenance=yes"), set and removed on the worker
`k8s-w1.lab`. The challenge is about another taint and other objects: you
will do it on your own, at the end.

Related page: [Affinity, tolerations and taints](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/affinity-tolerations-and-taints/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-taints-tolerations-placement
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

First look at the taints of the two nodes:

```bash
kubectl get nodes -o custom-columns=NOM:.metadata.name,TAINTS:.spec.taints
```

```text
NOM          TAINTS
k8s-cp.lab   <none>
k8s-w1.lab   <none>
```

No taint, not even on the control plane: on this lab cluster, it was removed
so that Pods can be placed there. For the scratch taints to show, this
course's Pods ask for the worker with a `nodeSelector` on the
`kubernetes.io/hostname` label. Without it, the scheduler would simply send
them to the control plane.

Create the namespace and a `resident` Pod, placed directly on the worker:

```bash
kubectl create namespace essai-taint; kubectl run resident --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeName":"k8s-w1.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/resident -n essai-taint --timeout=120s
```

```text
namespace/essai-taint created
pod/resident created
pod/resident condition met
```

## 🎁 Exercise 1: the tolerations a Pod gets by default

You wrote no toleration for `resident`. Yet read its tolerations:

```bash
kubectl get pod resident -n essai-taint -o jsonpath='{range .spec.tolerations[*]}{.key} {.operator} {.effect} {.tolerationSeconds}{"\n"}{end}'
```

```text
node.kubernetes.io/not-ready Exists NoExecute 300
node.kubernetes.io/unreachable Exists NoExecute 300
```

The API added two. When a node becomes unreachable or is no longer ready,
Kubernetes sets a `NoExecute` taint on it. These tolerations leave the Pod in
place for 300 seconds before evicting it: that is the delay before a Pod
leaves a node that went down.

## 🚧 Exercise 2: NoSchedule evicts nobody

Set a `NoSchedule` taint on the worker:

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:NoSchedule; sleep 10; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab tainted
resident   Running   k8s-w1.lab
```

`resident` still runs. Create a Pod that asks for the worker:

```bash
kubectl run arrivant --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"}}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod/arrivant created
arrivant   Pending   <none>
resident   Running   k8s-w1.lab
```

`arrivant` ("newcomer") stays `Pending`. `NoSchedule` refuses new Pods, but
does not touch the ones already running.

## 🎯 Exercise 3: a toleration aimed at the wrong effect

Create a Pod that does tolerate the taint's key and value, but with the
`NoExecute` effect instead of `NoSchedule`:

```bash
kubectl run mal-tolerant --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"},"tolerations":[{"key":"essai-maintenance","operator":"Equal","value":"oui","effect":"NoExecute"}]}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod/mal-tolerant created
arrivant       Pending   <none>
mal-tolerant   Pending   <none>
resident       Running   k8s-w1.lab
```

```bash
kubectl get events -n essai-taint --field-selector involvedObject.name=mal-tolerant,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/2 nodes are available: 1 node(s) didn't match Pod's node affinity/selector, 1 node(s) had untolerated taint(s). preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

`mal-tolerant` stays `Pending`, like `arrivant`. A toleration must match the
taint's key, value and effect. The scheduler reports an untolerated taint on
one node, and an unmet selector on the other.

## 🃏 Exercise 4: a universal toleration

A toleration with `operator: Exists` and no key tolerates every taint:

```bash
kubectl run tout-tolerant --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"},"tolerations":[{"operator":"Exists"}]}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
pod/tout-tolerant created
arrivant        Pending   <none>
mal-tolerant    Pending   <none>
resident        Running   k8s-w1.lab
tout-tolerant   Running   k8s-w1.lab
```

`tout-tolerant` ("tolerates-all") runs on the worker. It is the toleration of
agents that must be everywhere, such as networking ones. On an ordinary Pod,
it also keeps the Pod on a node you want to empty.

## 🚪 Exercise 5: NoExecute evicts

Replace the taint with a `NoExecute` taint, after deleting the two pending
Pods. The command waits 45 seconds, the time for `resident` to stop:

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:NoSchedule-; kubectl delete pod arrivant mal-tolerant -n essai-taint --wait=false >/dev/null; kubectl taint node k8s-w1.lab essai-maintenance=oui:NoExecute; sleep 45; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab untainted
node/k8s-w1.lab tainted
tout-tolerant   Running   k8s-w1.lab
```

`resident` is gone, `tout-tolerant` stayed. `resident`'s events say who
evicted it:

```bash
kubectl get events -n essai-taint --field-selector involvedObject.name=resident -o custom-columns=RAISON:.reason,MESSAGE:.message --no-headers | grep -E 'TaintManager|Killing'
```

```text
TaintManagerEviction   Marking for deletion Pod essai-taint/resident
Killing                Stopping container resident
```

`TaintManagerEviction`: the taint controller deleted the Pod. A Pod without a
controller does not come back. A Deployment's Pod would be recreated
elsewhere. Before setting a `NoExecute`, check what runs on the node.

## 🌤️ Exercise 6: PreferNoSchedule, a preference

Replace the taint with a `PreferNoSchedule` taint, and create a Pod that asks
for the worker, without any toleration:

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:NoExecute-; kubectl taint node k8s-w1.lab essai-maintenance=oui:PreferNoSchedule; kubectl run souple --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-taint --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-w1.lab"}}}' -- sleep 3600; sleep 8; kubectl get pods -n essai-taint -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName --no-headers
```

```text
node/k8s-w1.lab untainted
node/k8s-w1.lab tainted
pod/souple created
souple          Running   k8s-w1.lab
tout-tolerant   Running   k8s-w1.lab
```

`souple` ("flexible") runs on the worker. `PreferNoSchedule` asks the
scheduler to avoid the node when it has a choice. Here, the `nodeSelector`
leaves it none.

## 🔒 Exercise 7: cordon is a taint

Remove the scratch taint, then mark the worker unschedulable with
`kubectl cordon`, and read its taints:

```bash
kubectl taint node k8s-w1.lab essai-maintenance=oui:PreferNoSchedule-; kubectl cordon k8s-w1.lab; kubectl get node k8s-w1.lab -o jsonpath='{range .spec.taints[*]}{.key}={.value}:{.effect}{"\n"}{end}'
```

```text
node/k8s-w1.lab untainted
node/k8s-w1.lab cordoned
node.kubernetes.io/unschedulable=:NoSchedule
```

`cordon` sets the `node.kubernetes.io/unschedulable:NoSchedule` taint. It
therefore has the same effect as in exercise 2: running Pods stay, new ones
are refused. `uncordon` removes it:

```bash
kubectl uncordon k8s-w1.lab; kubectl get node k8s-w1.lab -o jsonpath='taints={.spec.taints}{"\n"}'
```

```text
node/k8s-w1.lab uncordoned
taints=
```

## 🧹 Clean-up

Delete the scratch namespace and check that no taint is left on the worker:

```bash
kubectl delete namespace essai-taint; kubectl get node k8s-w1.lab -o jsonpath='taints={.spec.taints}{"\n"}'
```

```text
namespace "essai-taint" deleted
taints=
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-taints-tolerations-placement
dsoxlab check cka-taints-tolerations-placement
```

```text
╭─ Result: cka-taints-tolerations-placement ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests           │
╰────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a node to reserve for production, an
application that goes there, and another that does not.

```bash
dsoxlab run cka-taints-tolerations-placement
dsoxlab challenge cka-taints-tolerations-placement
```
