# Give each replica a stable identity with a StatefulSet

The lesson shows a StatefulSet: numbered Pods, a stable DNS name per Pod, and
a volume of its own for each replica. This course adds cases the lesson does
not show: numbering that starts at 1, a volume template you can no longer
change, a never-ready Pod that blocks the next ones, a Service that publishes
Pods that are not ready yet, and `minReadySeconds`, which slows the rollout
down.

You work in a scratch namespace, `essai-sts`, with three scratch
StatefulSets: `registre`, `pair` and `lent` ("register", "peer" and "slow").
Each one has its headless Service (no Service address, `clusterIP: None`),
which gives each Pod a DNS name. The challenge is about other objects: you
will do it on your own, at the end.

Related page: [StatefulSets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/statefulsets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-statefulset-identite-stable
```

You are now connected to `k8s-kind.lab`, a machine that runs a kind cluster.
Your kubectl already targets it. Its default storage class, `standard`,
creates volumes on demand.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.0 (kind cluster).

## 🔢 Exercise 1: start numbering at 1

By default, a StatefulSet's Pods are numbered from 0. The `ordinals.start`
field changes the first number. Create the namespace, then a `registre`
StatefulSet with three replicas that starts at 1. Each replica gets a 64 Mi
volume from the `fiches` ("cards") template:

```bash
kubectl create namespace essai-sts
cat <<YAML | kubectl apply -n essai-sts -f -
apiVersion: v1
kind: Service
metadata:
  name: registre
spec:
  clusterIP: None
  publishNotReadyAddresses: false
  selector: {app: registre}
  ports: [{port: 80}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: registre
spec:
  serviceName: registre
  replicas: 3
  ordinals: {start: 1}
  selector:
    matchLabels: {app: registre}
  template:
    metadata:
      labels: {app: registre}
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet: {path: /, port: 80}
            periodSeconds: 2
  volumeClaimTemplates:
    - metadata: {name: fiches}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 64Mi}}
YAML
kubectl rollout status statefulset/registre -n essai-sts --timeout=240s; kubectl get pods,pvc -n essai-sts
```

```text
namespace/essai-sts created
service/registre created
statefulset.apps/registre created
Waiting for 3 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 1 pods to be ready...
Waiting for 1 pods to be ready...
partitioned roll out complete: 3 new pods have been updated...
NAME             READY   STATUS    RESTARTS   AGE
pod/registre-1   1/1     Running   0          14s
pod/registre-2   1/1     Running   0          10s
pod/registre-3   1/1     Running   0          5s

NAME                                      STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/fiches-registre-1   Bound    pvc-ffe860c6-19e3-4a5c-aa75-03b9687bf8df   64Mi       RWO            standard       <unset>                 14s
persistentvolumeclaim/fiches-registre-2   Bound    pvc-57654403-ad18-4e4d-9899-379e3abb074a   64Mi       RWO            standard       <unset>                 10s
persistentvolumeclaim/fiches-registre-3   Bound    pvc-6d0e9fb1-9c2d-4486-aa67-2104414bfccb   64Mi       RWO            standard       <unset>                 5s
```

The Pods are called `registre-1` to `registre-3`, and each volume claim
carries the template's name followed by the Pod's name: `fiches-registre-1`,
and so on. The Pods started one after the other (look at their age): a Pod is
only created when the previous one is ready.

## 🔒 Exercise 2: the volume template cannot be changed

Try to grow the volume template to 128 Mi:

```bash
kubectl patch statefulset registre -n essai-sts --type json -p '[{"op":"replace","path":"/spec/volumeClaimTemplates/0/spec/resources/requests/storage","value":"128Mi"}]'
```

```text
The StatefulSet "registre" is invalid: spec.volumeClaimTemplates: Invalid value: [{"name":"fiches","Spec":{"AccessModes":["ReadWriteOnce"],"Selector":null,"Resources":{"Limits":null,"Requests":{"storage":"128Mi"}},"VolumeName":"","StorageClassName":null,"VolumeMode":"Filesystem","DataSource":null,"DataSourceRef":null,"VolumeAttributesClassName":null},"Status":{"Phase":"Pending","AccessModes":null,"Capacity":null,"Conditions":null,"AllocatedResources":null,"AllocatedResourceStatuses":null,"CurrentVolumeAttributesClassName":null,"ModifyVolumeStatus":null,"HealthStatus":null}}]: field is immutable
```

The end of the message is the only useful part: `field is immutable`. Once
the StatefulSet is created, `volumeClaimTemplates` no longer moves. To grow
the volumes, you must grow each existing claim (if the class allows it), or
recreate the StatefulSet.

## 🧱 Exercise 3: a never-ready Pod blocks the next ones

Create a second StatefulSet, `pair`, whose readiness probe targets a page
that does not exist, `/absent`:

```bash
cat <<YAML | kubectl apply -n essai-sts -f -
apiVersion: v1
kind: Service
metadata:
  name: pair
spec:
  clusterIP: None
  publishNotReadyAddresses: false
  selector: {app: pair}
  ports: [{port: 80}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pair
spec:
  serviceName: pair
  replicas: 3
  
  selector:
    matchLabels: {app: pair}
  template:
    metadata:
      labels: {app: pair}
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet: {path: /absent, port: 80}
            periodSeconds: 2
  volumeClaimTemplates:
    - metadata: {name: fiches}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 64Mi}}
YAML
sleep 40; kubectl get pods -n essai-sts -l app=pair
```

```text
service/pair created
statefulset.apps/pair created
NAME     READY   STATUS    RESTARTS   AGE
pair-0   0/1     Running   0          40s
```

After 40 seconds, only one Pod exists: `pair-0`. It runs, but it is not
ready, and the StatefulSet waits for it to be ready before creating `pair-1`.
Read its state and the probe's last complaint:

```bash
kubectl get pod pair-0 -n essai-sts -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}{"\n"}'; kubectl get events -n essai-sts --field-selector involvedObject.name=pair-0,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
False
Readiness probe failed: HTTP probe failed with statuscode: 404
```

The probe gets a 404. With the default policy (`OrderedReady`), a single
blocked Pod stops the whole startup. When a StatefulSet stays at one Pod,
first look at the readiness of the last Pod created.

## 📣 Exercise 4: publish Pods that are not ready yet

Look up `pair-0`'s DNS name from a throwaway Pod. The name ends with a dot, so
that busybox does not walk its search list:

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sts --restart=Never --rm -i --quiet -- sh -c 'sleep 2; nslookup pair-0.pair.essai-sts.svc.cluster.local.'; echo "code $?"
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53

** server can't find pair-0.pair.essai-sts.svc.cluster.local.: NXDOMAIN

** server can't find pair-0.pair.essai-sts.svc.cluster.local.: NXDOMAIN

pod essai-sts/sonde terminated (Error)
code 1
```

`NXDOMAIN`: the name does not exist yet. DNS only publishes ready Pods. Yet
some clustered applications need to find each other before they are ready.
The headless Service's `publishNotReadyAddresses` field changes that:

```bash
kubectl patch service pair -n essai-sts --type merge -p '{"spec":{"publishNotReadyAddresses":true}}'; sleep 5; kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sts --restart=Never --rm -i --quiet -- sh -c 'sleep 2; nslookup pair-0.pair.essai-sts.svc.cluster.local.' | grep -A1 Name
```

```text
service/pair patched
Name:	pair-0.pair.essai-sts.svc.cluster.local
Address: 10.244.0.92
```

The name resolves, although `pair-0` is still not ready. This setting is
meant for a StatefulSet's headless Service, not for a Service that receives
clients' traffic.

## 🐢 Exercise 5: minReadySeconds slows the rollout down

Delete `pair` and create `lent`, with `minReadySeconds: 15`: a ready Pod only
counts as available after 15 seconds of continuous readiness. Look at the
state 25 seconds after creation (`prêts` means "ready", `disponibles` means
"available"):

```bash
kubectl delete statefulset pair -n essai-sts; cat <<YAML | kubectl apply -n essai-sts -f -
apiVersion: v1
kind: Service
metadata:
  name: lent
spec:
  clusterIP: None
  publishNotReadyAddresses: false
  selector: {app: lent}
  ports: [{port: 80}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: lent
spec:
  serviceName: lent
  replicas: 3
  minReadySeconds: 15
  selector:
    matchLabels: {app: lent}
  template:
    metadata:
      labels: {app: lent}
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet: {path: /, port: 80}
            periodSeconds: 2
  volumeClaimTemplates:
    - metadata: {name: fiches}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 64Mi}}
YAML
sleep 25; kubectl get pods -n essai-sts -l app=lent; kubectl get statefulset lent -n essai-sts -o jsonpath='prêts={.status.readyReplicas} disponibles={.status.availableReplicas}{"\n"}'
```

```text
statefulset.apps "pair" deleted from essai-sts namespace
service/lent created
statefulset.apps/lent created
NAME     READY   STATUS    RESTARTS   AGE
lent-0   1/1     Running   0          25s
lent-1   0/1     Pending   0          3s
prêts=1 disponibles=1
```

`lent-0` waited its 15 seconds before `lent-1` was created. `lent-1` has been
ready for 5 seconds, but is not available yet: `prêts=2`, `disponibles=1`.
This delay gives time to see a Pod that starts well then falls, before moving
on to the next one.

## 🧹 Clean-up

Delete the scratch namespace. The volume claims go with it:

```bash
kubectl delete namespace essai-sts
```

```text
namespace "essai-sts" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-statefulset-identite-stable
dsoxlab check cka-statefulset-identite-stable
```

```text
╭─ Result: cka-statefulset-identite-stable ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests          │
╰───────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a three-replica directory, each replica
with its own name and its own data.

```bash
dsoxlab run cka-statefulset-identite-stable
dsoxlab challenge cka-statefulset-identite-stable
```
