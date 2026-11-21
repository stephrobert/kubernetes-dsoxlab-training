# Create your StorageClass and get a volume no administrator created

The lesson shows a StorageClass that has volumes created on demand by a
provisioner. This course tries a class's settings against the lab's
provisioner, and adds cases the lesson does not show: an `Immediate` class
that cannot work with this provisioner, a volume that cannot be expanded, a
provisioner-specific parameter that stores volumes differently, and a volume
that disappears with its claim.

You work in a scratch namespace, `essai-classe`, with two scratch classes
(`classe-immediate` and `classe-rangee`) and `carnet` ("notebook") claims.
The challenge is about other objects: you will do it on your own, at the end.

Related page: [StorageClass](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/storageclass/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-storageclass-provisionnement-dynamique
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and local-path-provisioner v0.0.37.

Create the namespace, then read the class installed by the lab and its
settings:

```bash
kubectl create namespace essai-classe; kubectl get storageclass; kubectl get storageclass local-path -o jsonpath='{.provisioner} {.volumeBindingMode} {.reclaimPolicy} expansion={.allowVolumeExpansion}{"\n"}'
```

```text
namespace/essai-classe created
NAME         PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
local-path   rancher.io/local-path   Delete          WaitForFirstConsumer   false                  5m32s
rancher.io/local-path WaitForFirstConsumer Delete expansion=
```

The `local-path` class is served by the `rancher.io/local-path` provisioner.
It creates volumes for the first Pod that uses them (`WaitForFirstConsumer`),
deletes them with their claim (`Delete`), and does not allow expanding them.
The provisioner itself runs as a Deployment:

```bash
kubectl -n local-path-storage get deployment -o jsonpath='{.items[0].spec.template.spec.containers[0].image}{"\n"}'
```

```text
docker.io/rancher/local-path-provisioner:v0.0.37@sha256:e757967a5ec338f6a9b371c5a9688bedaa8c3578ea3dd4db329ea0084be0a86f
```

## ⏱️ Exercise 1: an Immediate class

Create an identical class, but with `volumeBindingMode: Immediate`, and a
claim that uses it, without any Pod:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: classe-immediate
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: Immediate
YAML
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-immediat
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: classe-immediate
  resources: {requests: {storage: 64Mi}}
YAML
sleep 15; kubectl get pvc carnet-immediat -n essai-classe
```

```text
storageclass.storage.k8s.io/classe-immediate created
persistentvolumeclaim/carnet-immediat created
NAME              STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS       VOLUMEATTRIBUTESCLASS   AGE
carnet-immediat   Pending                                      classe-immediate   <unset>                 15s
```

The claim stays `Pending`. The events say why:

```bash
kubectl get events -n essai-classe --field-selector involvedObject.name=carnet-immediat -o custom-columns=RAISON:.reason,MESSAGE:.message | tail -3
```

```text
Provisioning           External provisioner is provisioning volume for claim "essai-classe/carnet-immediat"
ProvisioningFailed     failed to provision volume with StorageClass "classe-immediate": configuration error, no node was specified
ExternalProvisioning   Waiting for a volume to be created either by the external provisioner 'rancher.io/local-path' or manually by the system administrator. If volume creation is delayed, please verify that the provisioner is running and correctly registered.
```

`no node was specified`: local-path creates the volume in a directory of a
node, and it must know which one. With `Immediate`, the claim is handled
before any Pod is placed, hence without a node. With local storage, only
`WaitForFirstConsumer` works: the volume is created on the first Pod's node.

## 📏 Exercise 2: expand a volume

Create a 64 Mi claim on `local-path`, and a Pod that writes a page into it:

```bash
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: carnet-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo page 1 > /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet}
YAML
kubectl wait --for=condition=Ready pod/carnet-pod -n essai-classe --timeout=120s; kubectl get pvc carnet -n essai-classe
```

```text
persistentvolumeclaim/carnet created
pod/carnet-pod created
pod/carnet-pod condition met
NAME     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
carnet   Bound    pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd   64Mi       RWO            local-path     <unset>                 5s
```

Now ask for 128 Mi:

```bash
kubectl patch pvc carnet -n essai-classe --type merge -p '{"spec":{"resources":{"requests":{"storage":"128Mi"}}}}'
```

```text
Error from server (Forbidden): persistentvolumeclaims "carnet" is forbidden: only dynamically provisioned pvc can be resized and the storageclass that provisions the pvc must support resize
```

Refused on submission: the `local-path` class does not have
`allowVolumeExpansion: true`, as you read at the start. The API refuses,
before any provisioner. For a volume that will need to grow, the class is
chosen when the claim is created.

## 🗂️ Exercise 3: store volumes differently

A class's `parameters` field is passed to the provisioner, which alone knows
how to read it. local-path accepts `pathPattern`, to choose each volume's
directory. Create a class that stores volumes by namespace then by claim name,
with a claim and a Pod:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: classe-rangee
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  pathPattern: "{{ .PVC.Namespace }}/{{ .PVC.Name }}"
YAML
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-range
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: classe-rangee
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: range-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo range > /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet-range}
YAML
sleep 20; kubectl get pvc carnet-range -n essai-classe; kubectl get events -n essai-classe --field-selector involvedObject.name=carnet-range,reason=ProvisioningFailed -o jsonpath='{.items[0].message}{"\n"}'
```

```text
storageclass.storage.k8s.io/classe-rangee created
persistentvolumeclaim/carnet-range created
pod/range-pod created
NAME           STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS    VOLUMEATTRIBUTESCLASS   AGE
carnet-range   Pending                                      classe-rangee   <unset>                 20s
failed to provision volume with StorageClass "classe-rangee": failed to create path from pattern {{ .PVC.Namespace }}/{{ .PVC.Name }}: pathPattern must start with {{ .PVC.Namespace }}/{{ .PVC.Name }}/: essai-classe/carnet-range
```

The claim stays `Pending`, and the `ProvisioningFailed` event explains why:
this version of the provisioner requires the pattern to start with
`{{ .PVC.Namespace }}/{{ .PVC.Name }}/`, with one level below. The API
accepted the class without checking anything: it does not know the
provisioners' parameters. A class's parameters cannot be changed: delete
everything and recreate the class with a `donnees` ("data") subdirectory:

```bash
kubectl delete pod range-pod -n essai-classe; kubectl delete pvc carnet-range -n essai-classe; kubectl delete storageclass classe-rangee; cat <<'YAML' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: classe-rangee
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  pathPattern: "{{ .PVC.Namespace }}/{{ .PVC.Name }}/donnees"
YAML
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-range
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: classe-rangee
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: range-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo range > /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet-range}
YAML
kubectl wait --for=condition=Ready pod/range-pod -n essai-classe --timeout=120s
```

```text
pod "range-pod" deleted from essai-classe namespace
persistentvolumeclaim "carnet-range" deleted from essai-classe namespace
storageclass.storage.k8s.io "classe-rangee" deleted
storageclass.storage.k8s.io/classe-rangee created
persistentvolumeclaim/carnet-range created
pod/range-pod created
pod/range-pod condition met
```

Compare the paths of the two volumes on the node:

```bash
for p in carnet carnet-range; do V=$(kubectl get pvc $p -n essai-classe -o jsonpath='{.spec.volumeName}'); kubectl get pv $V -o jsonpath='{.metadata.name} -> {.spec.hostPath.path}{.spec.local.path}{"\n"}'; done
```

```text
pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd -> /opt/local-path-provisioner/pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd_essai-classe_carnet
pvc-535fedff-1ef9-4688-8873-d145bce7342d -> /opt/local-path-provisioner/essai-classe/carnet-range/donnees
```

The first volume carries local-path's default name. The second follows the
pattern: `essai-classe/carnet-range/donnees`.

## ♻️ Exercise 4: same name, new volume

Delete the Pod and the `carnet` claim, then look for its volume (`avant`
means "before"):

```bash
V1=$(kubectl get pvc carnet -n essai-classe -o jsonpath='{.spec.volumeName}'); echo "avant : $V1"; kubectl delete pod carnet-pod -n essai-classe; kubectl delete pvc carnet -n essai-classe; sleep 5; kubectl get pv $V1; echo "pv : code $?"
```

```text
avant : pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd
pod "carnet-pod" deleted from essai-classe namespace
persistentvolumeclaim "carnet" deleted from essai-classe namespace
Error from server (NotFound): persistentvolumes "pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd" not found
pv : code 1
```

The volume disappeared with the claim: that is the class's `Delete` policy.
Recreate an identical `carnet` claim, and a Pod that reads the page written in
exercise 2 (`après` means "after"):

```bash
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: carnet-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "ls /data; cat /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet}
YAML
kubectl wait --for=condition=Ready pod/carnet-pod -n essai-classe --timeout=120s; echo "après : $(kubectl get pvc carnet -n essai-classe -o jsonpath='{.spec.volumeName}')"; kubectl logs carnet-pod -n essai-classe
```

```text
persistentvolumeclaim/carnet created
pod/carnet-pod created
pod/carnet-pod condition met
après : pvc-318a289a-046c-4f91-a070-c0dd9abf4673
cat: can't open '/data/page': No such file or directory
```

Same claim name, but a new, empty volume: the page is lost. With `Delete`,
deleting a claim deletes the data. For data you want to keep, the class must
use `Retain`.

## 🧹 Clean-up

Delete the scratch namespace and the two classes, which belong to no
namespace:

```bash
kubectl delete namespace essai-classe; kubectl delete storageclass classe-immediate classe-rangee
```

```text
namespace "essai-classe" deleted
storageclass.storage.k8s.io "classe-immediate" deleted
storageclass.storage.k8s.io "classe-rangee" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-storageclass-provisionnement-dynamique
dsoxlab check cka-storageclass-provisionnement-dynamique
```

```text
╭─ Result: cka-storageclass-provisionnement-dynamique ─╮
│  0 / 100 pts                                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests                     │
╰──────────────────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a class that keeps its volumes, and a
volume created for you by the provisioner.

```bash
dsoxlab run cka-storageclass-provisionnement-dynamique
dsoxlab challenge cka-storageclass-provisionnement-dynamique
```
