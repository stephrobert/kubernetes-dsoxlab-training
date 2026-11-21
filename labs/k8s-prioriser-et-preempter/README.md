# Prioritize Pods and watch a preemption

The lesson shows PriorityClasses: a priority value given to Pods, and
preemption, when the scheduler removes lower-priority Pods to make room for a
higher-priority one. This course adds cases the lesson does not show: a class
that does not exist, a priority written by hand, a class value you want to
change, and a preemption that overrides a PodDisruptionBudget.

You work in a scratch namespace, `essai-prio`, with two scratch classes,
`essai-fond` ("background", 500) and `essai-vital` ("vital", 50000), and the
`multi-worker2` node. The challenge is about other classes and the other
worker: you will do it on your own, at the end.

Related page: [Advanced scheduling](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/priority-and-preemption/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-prioriser-et-preempter
```

You are now connected to `k8s-kind.lab`. The lab created a kind cluster named
`multi` there, with one control plane and two workers, and your kubectl
targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.0 (kind cluster).

Create the namespace and the two scratch classes, then look at the nodes:

```bash
kubectl create namespace essai-prio; kubectl create priorityclass essai-fond --value=500; kubectl create priorityclass essai-vital --value=50000; kubectl get nodes
```

```text
namespace/essai-prio created
priorityclass.scheduling.k8s.io/essai-fond created
priorityclass.scheduling.k8s.io/essai-vital created
NAME                  STATUS   ROLES           AGE     VERSION
multi-control-plane   Ready    control-plane   3m59s   v1.37.0
multi-worker          Ready    <none>          3m48s   v1.37.0
multi-worker2         Ready    <none>          3m48s   v1.37.0
```

## ❓ Exercise 1: a class that does not exist

Create a Pod that asks for a class nobody created:

```bash
kubectl run orphelin --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-prio --overrides='{"spec":{"priorityClassName":"essai-inconnue"}}' -- sleep 3600
```

```text
Error from server (Forbidden): pods "orphelin" is forbidden: no PriorityClass with name essai-inconnue was found
```

The API refuses the Pod at creation. The `Priority` admission controller
looks for the class and does not find it. The Pod does not exist at all: it is
not waiting anywhere.

## ✍️ Exercise 2: write the priority by hand

A Pod has a `priority` field, a plain number. Try to write it yourself:

```bash
kubectl run tricheur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-prio --overrides='{"spec":{"priority":1000000}}' -- sleep 3600
```

```text
Error from server (Forbidden): pods "tricheur" is forbidden: the integer value of priority (1000000) must not be provided in pod spec; priority admission controller computed 0 from the given PriorityClass name
```

Refused: this field is filled in by the API from the class, never by the
user. Otherwise anyone could give themselves the highest priority. Create a
Pod that goes through the class, then read both fields (`classe` means
"class", `priorité` means "priority"):

```bash
kubectl run normal --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-prio --overrides='{"spec":{"priorityClassName":"essai-vital"}}' -- sleep 3600; kubectl get pod normal -n essai-prio -o jsonpath='classe={.spec.priorityClassName} priorité={.spec.priority}{"\n"}'
```

```text
pod/normal created
classe=essai-vital priorité=50000
```

The API copied the value of `essai-vital`, 50000, into the `priority` field.

## 🔒 Exercise 3: a class's value cannot be changed

Try to move `essai-fond` from 500 to 700:

```bash
kubectl patch priorityclass essai-fond --type merge -p '{"value":700}'
```

```text
The PriorityClass "essai-fond" is invalid: value: Forbidden: may not be changed in an update.
```

Refused. The value is copied into each Pod at creation. Changing it in the
class would leave the old Pods with the old value. To change a priority, you
create a new class, and move the Pods to it.

## ⚔️ Exercise 4: preemption overrides a budget

Look at what the `multi-worker2` worker has already reserved in CPU:

```bash
kubectl describe node multi-worker2 | grep -A4 'Allocated resources'
```

```text
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests   Limits
  --------           --------   ------
  cpu                100m (5%)  0 (0%)
```

Compute a CPU share such that three Pods fill the rest of the node (`alloué`
means "allocatable", `déjà demandé` "already requested", `part de chaque Pod`
"share of each Pod"). The share is kept in `~/part-cpu` for the next
commands:

```bash
A=$(kubectl get node multi-worker2 -o jsonpath='{.status.allocatable.cpu}'); case $A in *m) A=${A%m};; *) A=$((A*1000));; esac; R=$(kubectl describe node multi-worker2 | awk '/Allocated resources/{f=1} f&&$1=="cpu"{print $2; exit}' | tr -d m); PART=$(( (A - R) / 3 - 10 )); echo "alloué ${A}m, déjà demandé ${R}m, part de chaque Pod : ${PART}m"; echo $PART > ~/part-cpu
```

```text
alloué 2000m, déjà demandé 100m, part de chaque Pod : 623m
```

Create a `garde` ("guard") Deployment of three `essai-fond` Pods, each with
that share, on `multi-worker2`. Then protect it with a PodDisruptionBudget
(PDB) that requires three available Pods:

```bash
PART=$(cat ~/part-cpu); cat <<YAML | kubectl apply -n essai-prio -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: garde
spec:
  replicas: 3
  selector:
    matchLabels: {app: garde}
  template:
    metadata:
      labels: {app: garde}
    spec:
      priorityClassName: essai-fond
      nodeSelector: {kubernetes.io/hostname: multi-worker2}
      containers:
        - name: garde
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: [sleep, "3600"]
          resources:
            requests: {cpu: ${PART}m}
YAML
```

```text
kubectl rollout status deployment/garde -n essai-prio --timeout=120s; kubectl create poddisruptionbudget protege -n essai-prio --selector=app=garde --min-available=3; kubectl get pdb protege -n essai-prio
deployment.apps/garde created
Waiting for deployment spec update to be observed...
Waiting for deployment "garde" rollout to finish: 0 out of 3 new replicas have been updated...
Waiting for deployment "garde" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "garde" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "garde" rollout to finish: 2 of 3 updated replicas are available...
deployment "garde" successfully rolled out
poddisruptionbudget.policy/protege created
NAME      MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
protege   3               N/A               0                     0s
```

`ALLOWED DISRUPTIONS` is 0: the budget forbids removing a single `garde` Pod.
Now create a `vital` Pod, of class `essai-vital`, that asks for the same
share on the same, already full node:

```bash
PART=$(cat ~/part-cpu); cat <<YAML | kubectl apply -n essai-prio -f -
apiVersion: v1
kind: Pod
metadata:
  name: vital
spec:
  priorityClassName: essai-vital
  nodeSelector: {kubernetes.io/hostname: multi-worker2}
  containers:
    - name: vital
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: [sleep, "3600"]
      resources:
        requests: {cpu: ${PART}m}
YAML
```

```text
kubectl wait --for=condition=Ready pod/vital -n essai-prio --timeout=120s; kubectl get pods -n essai-prio -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName,CLASSE:.spec.priorityClassName
pod/vital created
pod/vital condition met
NOM                      ETAT      NOEUD           CLASSE
garde-69cf8f5868-5wjt9   Running   multi-worker2   essai-fond
garde-69cf8f5868-kcnjh   Pending   <none>          essai-fond
garde-69cf8f5868-njc79   Running   multi-worker2   essai-fond
normal                   Running   multi-worker2   essai-vital
vital                    Running   multi-worker2   essai-vital
```

`vital` runs. A `garde` Pod was removed, and the Deployment recreated another
one, which stays `Pending`: there is no room left for it. The events name the
removed Pod:

```bash
kubectl get events -n essai-prio --field-selector reason=Preempted -o custom-columns=OBJET:.involvedObject.name,MESSAGE:.message --no-headers | tail -2; kubectl get pdb protege -n essai-prio
```

```text
garde-69cf8f5868-cckx5   Preempted by pod 7667a9de-b1ff-410d-a3bd-8b1fe94bdcef on node multi-worker2
NAME      MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
protege   3               N/A               0                     33s
```

`Preempted by pod … on node multi-worker2`. The budget did not prevent the
preemption: the scheduler tries to respect PDBs, but if no other choice lets
it place the high-priority Pod, it overrides them. A PDB protects against
voluntary evictions, such as a `kubectl drain`, not against preemption.

## 🧹 Clean-up

Delete the namespace, the two classes, which belong to no namespace, and the
share file:

```bash
kubectl delete namespace essai-prio; kubectl delete priorityclass essai-fond essai-vital; rm -f ~/part-cpu
```

```text
namespace "essai-prio" deleted
priorityclass.scheduling.k8s.io "essai-fond" deleted
priorityclass.scheduling.k8s.io "essai-vital" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-prioriser-et-preempter
dsoxlab check k8s-prioriser-et-preempter
```

```text
╭─ Result: k8s-prioriser-et-preempter ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests     │
╰──────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: two classes, a full node, and an urgent Pod
that must make room for itself there.

```bash
dsoxlab run k8s-prioriser-et-preempter
dsoxlab challenge k8s-prioriser-et-preempter
```
