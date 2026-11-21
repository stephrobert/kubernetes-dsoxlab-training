# Read why four Pods stay Pending and get each one placed

The lesson shows how to read why a Pod stays `Pending`: the scheduler writes
its reason in a `FailedScheduling` event. This course adds cases the lesson
does not show: counting the nodes that really accept a Pod, an anti-affinity
that cannot be satisfied, a local volume attached to another node than the
one requested, and a Pod held back on purpose by a scheduling gate.

You work in a scratch namespace, `essai-attente`. The challenge is about
another namespace and other applications: you will do it on your own, at the
end.

Related page (in French): [Pods en Pending](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/pods-pending-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-placer-un-pod-pending
```

The lab adds a second worker, `k8s-w2.lab`. You are now connected to
`k8s-cp.lab`, the node that runs the kubeadm cluster (the control plane).
Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🔢 Exercise 1: count the nodes that accept a Pod

Create the namespace, and list the nodes with their taints' keys:

```bash
kubectl create namespace essai-attente; kubectl get nodes -o custom-columns=NOM:.metadata.name,TAINTS:.spec.taints[*].key
```

```text
namespace/essai-attente created
NOM          TAINTS
k8s-cp.lab   <none>
k8s-w1.lab   equipe
k8s-w2.lab   <none>
```

Three nodes, but `k8s-w1.lab` carries a taint, `equipe` ("team"), set by the
challenge. A Pod without a toleration therefore has only two possible nodes:
`k8s-cp.lab` and `k8s-w2.lab`. Before reasoning about a `Pending`, count the
nodes that accept this Pod, not all nodes.

## 🙅 Exercise 2: three Pods that must not meet

Create a 3-replica Deployment with a required anti-affinity: two `solitaire`
("loner") Pods must never share a node.

```bash
cat <<YAML | kubectl apply -n essai-attente -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: solitaire
spec:
  replicas: 3
  selector:
    matchLabels: {app: solitaire}
  template:
    metadata:
      labels: {app: solitaire}
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels: {app: solitaire}
              topologyKey: kubernetes.io/hostname
      containers:
        - {name: c, image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4, command: [sleep, "3600"]}
YAML
sleep 15; kubectl get pods -n essai-attente -l app=solitaire -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName
```

```text
deployment.apps/solitaire created
NOM                          ETAT      NOEUD
solitaire-55b5fddd6b-knw9f   Running   k8s-w2.lab
solitaire-55b5fddd6b-thr5f   Running   k8s-cp.lab
solitaire-55b5fddd6b-z5bns   Pending   <none>
```

Two Pods run, one on each free node, and the third waits. Read the
scheduler's reason:

```bash
P=$(kubectl get pods -n essai-attente -l app=solitaire --field-selector status.phase=Pending -o jsonpath='{.items[0].metadata.name}'); kubectl get events -n essai-attente --field-selector reason=FailedScheduling,involvedObject.name=$P -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/3 nodes are available: 1 node(s) had untolerated taint(s), 2 node(s) didn't match pod anti-affinity rules. preemption: 0/3 nodes are available: 1 Preemption is not helpful for scheduling, 2 No preemption victims found for incoming pod.
```

The scheduler details its refusal node by node: one node has an untolerated
taint, the other two already carry a `solitaire` Pod. The message does not
say what to do, it says which filter ruled out each node. Here, you would
need one more node, or an anti-affinity that is only preferred (`preferred`).

## 💾 Exercise 3: a volume that lives on another node

A `local` volume is attached to a precise node. Create one on `k8s-cp.lab`, a
claim bound to it, and a Pod that requires `k8s-w2.lab`:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: essai-carnet-local
spec:
  capacity: {storage: 64Mi}
  accessModes: [ReadWriteOnce]
  storageClassName: essai-locale
  local: {path: /tmp}
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - {key: kubernetes.io/hostname, operator: In, values: [k8s-cp.lab]}
YAML
cat <<YAML | kubectl apply -n essai-attente -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-local
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: essai-locale
  volumeName: essai-carnet-local
  resources: {requests: {storage: 64Mi}}
---
apiVersion: v1
kind: Pod
metadata:
  name: carnet
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-w2.lab}
  containers:
    - {name: c, image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4, command: [sleep, "3600"], volumeMounts: [{name: v, mountPath: /data}]}
  volumes:
    - {name: v, persistentVolumeClaim: {claimName: carnet-local}}
YAML
sleep 20; kubectl get pvc carnet-local -n essai-attente; kubectl get pod carnet -n essai-attente; kubectl get events -n essai-attente --field-selector reason=FailedScheduling,involvedObject.name=carnet -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
persistentvolume/essai-carnet-local created
persistentvolumeclaim/carnet-local created
pod/carnet created
NAME           STATUS   VOLUME               CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
carnet-local   Bound    essai-carnet-local   64Mi       RWO            essai-locale   <unset>                 20s
NAME     READY   STATUS    RESTARTS   AGE
carnet   0/1     Pending   0          20s
0/3 nodes are available: 1 node(s) didn't match PersistentVolume's node affinity, 1 node(s) didn't match Pod's node affinity/selector, 1 node(s) had untolerated taint(s). preemption: 0/3 nodes are available: 3 Preemption is not helpful for scheduling.
```

The claim is indeed bound (`Bound`), and yet the Pod waits. All three nodes
are ruled out, each for a reason: one is not the volume's node, another is
not the selector's node, the last one has a taint. The Pod asks for one node,
its volume imposes another: none satisfies both. A local volume is chosen
together with the node, not afterwards.

## 🚦 Exercise 4: a Pod held back on purpose

A scheduling gate (`schedulingGates`) stops the scheduler from handling a Pod
while it is there. Create a Pod with a gate:

```bash
kubectl run retenu --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-attente --overrides='{"spec":{"schedulingGates":[{"name":"essai.lab/feu-vert"}]}}' -- sleep 3600; sleep 5; kubectl get pod retenu -n essai-attente
```

```text
pod/retenu created
NAME     READY   STATUS            RESTARTS   AGE
retenu   0/1     SchedulingGated   0          5s
```

`SchedulingGated`: this is not a failure, the Pod waits to be released.
Remove the gate:

```bash
kubectl patch pod retenu -n essai-attente --type json -p '[{"op":"remove","path":"/spec/schedulingGates"}]'; sleep 8; kubectl get pod retenu -n essai-attente -o custom-columns=NOM:.metadata.name,ETAT:.status.phase,NOEUD:.spec.nodeName
```

```text
pod/retenu patched
NOM      ETAT      NOEUD
retenu   Running   k8s-w2.lab
```

The Pod is placed as soon as the gate disappears. A tool can thus prepare
Pods and only release them at the right time.

## 🧹 Clean-up

Delete the namespace and the PersistentVolume, which belongs to no namespace:

```bash
kubectl delete namespace essai-attente; kubectl delete pv essai-carnet-local
```

```text
namespace "essai-attente" deleted
persistentvolume "essai-carnet-local" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-placer-un-pod-pending
dsoxlab check cka-placer-un-pod-pending
```

```text
╭─ Result: cka-placer-un-pod-pending ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests    │
╰─────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: four `Pending` applications, one cause
each, to diagnose and then place.

```bash
dsoxlab run cka-placer-un-pod-pending
dsoxlab challenge cka-placer-un-pod-pending
```
