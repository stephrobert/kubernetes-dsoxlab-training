# Rebuild an incident from the Events of a namespace

The lesson shows Events: the messages the cluster's components leave on
objects. This course has you rebuild a series of failures from them, and adds
cases the lesson does not show: the events of a single object, a repeated
event that does not duplicate, the sort that tells who was hit first, how
long events are kept, and the events of a Deployment.

You work in a scratch namespace, `essai-journal`, with three failing Pods:
`introuvable`, `impatient` and `grossiste` ("not-found", "impatient" and
"bulk-buyer"). The challenge is about another namespace: you will do it on
your own, at the end.

Related page (in French): [Analyser les événements Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/analyser-evenements-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-reconstituer-un-incident-par-les-evenements
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create three failures, a few seconds apart: an image that does not exist
(`introuvable`), a container that exits with an error (`impatient`), and a Pod
that asks for 64 CPUs (`grossiste`). The command then waits 40 seconds:

```bash
kubectl create namespace essai-journal; kubectl run introuvable --image=registry.invalid/essai:1 -n essai-journal; sleep 4; kubectl run impatient --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-journal -- sh -c 'exit 3'; sleep 4; kubectl run grossiste --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-journal --overrides='{"spec":{"containers":[{"name":"g","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"64"}}}]}}' -- sleep 3600; sleep 40
```

```text
namespace/essai-journal created
pod/introuvable created
pod/impatient created
pod/grossiste created
```

## 🎯 Exercise 1: the events of a single object

`kubectl events --for` filters one object's events, and `--types` only keeps
warnings:

```bash
kubectl events -n essai-journal --for pod/impatient --types=Warning
```

```text
LAST SEEN          TYPE      REASON    OBJECT          MESSAGE
8s (x4 over 42s)   Warning   BackOff   Pod/impatient   Back-off restarting failed container impatient in pod impatient_essai-journal(d94b35c2-7661-4627-ae5f-ff1705a2ac5b)
```

A single line, although the container restarted several times:
`(x4 over 42s)` says this event happened 4 times in 42 seconds.

## 🔁 Exercise 2: a repeated event does not duplicate

Read this event's counter and its two dates (`NOMBRE` means "count",
`PREMIER` "first", `DERNIER` "last"):

```bash
kubectl get events -n essai-journal --field-selector involvedObject.name=impatient,reason=BackOff -o custom-columns=RAISON:.reason,NOMBRE:.count,PREMIER:.firstTimestamp,DERNIER:.lastTimestamp
```

```text
RAISON    NOMBRE   PREMIER                DERNIER
BackOff   4        2026-11-21T04:40:09Z   2026-11-21T04:40:43Z
```

Wait 90 seconds and read again:

```bash
sleep 90; kubectl get events -n essai-journal --field-selector involvedObject.name=impatient,reason=BackOff -o custom-columns=RAISON:.reason,NOMBRE:.count,PREMIER:.firstTimestamp,DERNIER:.lastTimestamp
```

```text
RAISON    NOMBRE   PREMIER                DERNIER
BackOff   5        2026-11-21T04:40:09Z   2026-11-21T04:41:38Z
```

The same Event object was updated: the counter goes up to 5, the first date
does not move, the last one moves forward. A Pod restarting in a loop
therefore does not create hundreds of events, but a single one whose counter
grows.

## 🥇 Exercise 3: who was hit first?

Sort the warnings by their first date:

```bash
kubectl get events -n essai-journal --field-selector type=Warning --sort-by=.firstTimestamp -o custom-columns=PREMIER:.firstTimestamp,OBJET:.involvedObject.name,RAISON:.reason
```

```text
PREMIER                OBJET         RAISON
2026-11-21T04:40:03Z   introuvable   Failed
2026-11-21T04:40:03Z   introuvable   Failed
2026-11-21T04:40:04Z   introuvable   Failed
2026-11-21T04:40:09Z   impatient     BackOff
2026-11-21T04:40:11Z   grossiste     FailedScheduling
```

`introuvable` was hit first, then `impatient`, then `grossiste`: the order in
which the failures were created. Now sort by the last date:

```bash
kubectl get events -n essai-journal --field-selector type=Warning --sort-by=.lastTimestamp -o custom-columns=DERNIER:.lastTimestamp,OBJET:.involvedObject.name,RAISON:.reason
```

```text
DERNIER                OBJET         RAISON
2026-11-21T04:40:11Z   grossiste     FailedScheduling
2026-11-21T04:41:37Z   introuvable   Failed
2026-11-21T04:41:37Z   introuvable   Failed
2026-11-21T04:41:38Z   impatient     BackOff
2026-11-21T04:42:18Z   introuvable   Failed
```

The order changes completely: repeating failures keep coming back up. To find
the start of an incident, sort by `firstTimestamp`. The default sort of
`kubectl get events` is not made for that.

## ⏳ Exercise 4: how long do events stay?

How long events are kept is set on the API server, with the `--event-ttl`
option. Look for it in its manifest:

```bash
sudo grep -c -- '--event-ttl' /etc/kubernetes/manifests/kube-apiserver.yaml
```

```text
0
```

Absent: the default value applies, one hour. Yesterday's incident therefore
has no event left to show. To keep the history, you must copy events
elsewhere before they expire.

## 🚀 Exercise 5: the events of a Deployment

Create a Deployment, scale it to 3 replicas, and read its events:

```bash
kubectl create deployment etalage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-journal --replicas=1 -- sleep 3600 >/dev/null; kubectl scale deployment etalage -n essai-journal --replicas=3; sleep 5; kubectl events -n essai-journal --for deployment/etalage
```

```text
deployment.apps/etalage scaled
LAST SEEN   TYPE     REASON              OBJECT               MESSAGE
5s          Normal   ScalingReplicaSet   Deployment/etalage   Scaled up replica set etalage-75b6945bb6 from 0 to 1
5s          Normal   ScalingReplicaSet   Deployment/etalage   Scaled up replica set etalage-75b6945bb6 from 1 to 3
```

The Deployment only talks about its ReplicaSet (`ScalingReplicaSet`). A Pod's
errors are on the Pod, and Pod creation errors on the ReplicaSet: to rebuild
an incident, you must read each level.

## 🧹 Clean-up

Delete the scratch namespace. Its events go with it:

```bash
kubectl delete namespace essai-journal
```

```text
namespace "essai-journal" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-reconstituer-un-incident-par-les-evenements
dsoxlab check k8s-reconstituer-un-incident-par-les-evenements
```

```text
╭─ Result: k8s-reconstituer-un-incident-par-les-evenements ─╮
│  0 / 100 pts                                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                          │
╰───────────────────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a namespace where several applications are
failing, and the report that says what happened to each of them, and in which
order.

```bash
dsoxlab run k8s-reconstituer-un-incident-par-les-evenements
dsoxlab challenge k8s-reconstituer-un-incident-par-les-evenements
```
