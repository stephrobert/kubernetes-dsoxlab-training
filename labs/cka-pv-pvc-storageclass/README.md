# A persistent volume: PersistentVolume, PersistentVolumeClaim and a Pod that writes

The lesson shows a PersistentVolume (PV) created by hand, a
PersistentVolumeClaim (PVC) that binds to it, and a Pod that writes into it.
This course adds cases the lesson does not show: choosing a specific PV by a
label, receiving more than you asked for, sharing a volume between two Pods
through subdirectories, mounting a volume read-only, and deleting a PVC that
is still in use.

You work in a scratch namespace, `essai-stock`, with two PVs (`pv-rapide` and
`pv-lent`: "fast" and "slow") and a PVC `reserve` ("store"). The PVs write to
the disk of the worker `k8s-w1.lab`, under `/tmp`. The challenge is about
other objects: you will do it on your own, at the end.

Related page: [Storage in Kubernetes](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/storage/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-pv-pvc-storageclass
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The cluster has no
storage provisioner: every PV is created by hand.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and two identical 2 Gi PVs, which differ only by their
`niveau` ("level") label. They use a directory of the worker (`hostPath`),
and `nodeAffinity` forces any Pod that uses them to run on that worker:

```bash
kubectl create namespace essai-stock; for n in rapide lent; do cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-$n
  labels: {niveau: $n}
spec:
  capacity: {storage: 2Gi}
  accessModes: [ReadWriteOnce]
  storageClassName: essai
  persistentVolumeReclaimPolicy: Retain
  hostPath: {path: /tmp/essai-stock-$n, type: DirectoryOrCreate}
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - {key: kubernetes.io/hostname, operator: In, values: [k8s-w1.lab]}
YAML
done; kubectl get pv pv-rapide pv-lent
```

```text
namespace/essai-stock created
persistentvolume/pv-rapide created
persistentvolume/pv-lent created
NAME        CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM   STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
pv-rapide   2Gi        RWO            Retain           Available           essai          <unset>                          0s
pv-lent     2Gi        RWO            Retain           Available           essai          <unset>                          0s
```

Both PVs are `Available`: free, waiting for a claim. Their `essai` class does
not exist as an object: it is just a label that pairs PVs and PVCs carrying
the same name.

## 🎯 Exercise 1: choose your PV by a label

A PVC can carry a `selector`, to bind only to a PV that carries certain
labels. Ask for 500 Mi, on a `niveau: lent` PV:

```bash
cat <<'YAML' | kubectl apply -n essai-stock -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: reserve
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: essai
  resources: {requests: {storage: 500Mi}}
  selector:
    matchLabels: {niveau: lent}
YAML
sleep 3; kubectl get pvc reserve -n essai-stock; kubectl get pv pv-rapide pv-lent
```

```text
persistentvolumeclaim/reserve created
NAME      STATUS   VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
reserve   Bound    pv-lent   2Gi        RWO            essai          <unset>                 3s
NAME        CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM                 STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
pv-rapide   2Gi        RWO            Retain           Available                         essai          <unset>                          3s
pv-lent     2Gi        RWO            Retain           Bound       essai-stock/reserve   essai          <unset>                          3s
```

The PVC bound to `pv-lent`, and `pv-rapide` stays free. Without a `selector`,
Kubernetes would have taken one of the two, and you could not tell which.

## 📏 Exercise 2: ask for 500 Mi, get 2 Gi

Compare the requested size with the size obtained (`demandé` means
"requested", `lié` means "bound"):

```bash
kubectl get pvc reserve -n essai-stock -o jsonpath='demandé {.spec.resources.requests.storage}, lié {.status.capacity.storage}{"\n"}'
```

```text
demandé 500Mi, lié 2Gi
```

A PV binds whole to a single PVC. The PVC therefore receives the PV's entire
capacity, even if it asked for less. With hand-made PVs, plan sizes close to
the requests, or space stays reserved without being used.

## 📂 Exercise 3: two Pods, one volume, two subdirectories

The `subPath` field mounts a subdirectory of the volume instead of its root.
Create two Pods that mount the same PVC, each in its own subdirectory, and
write a note there:

```bash
for a in a b; do cat <<YAML | kubectl apply -n essai-stock -f -
apiVersion: v1
kind: Pod
metadata:
  name: atelier-$a
spec:
  containers:
    - name: atelier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo ecrit par atelier-$a > /travail/note; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /travail, subPath: atelier-$a}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: reserve}
YAML
done; kubectl wait --for=condition=Ready pod/atelier-a pod/atelier-b -n essai-stock --timeout=120s
```

```text
pod/atelier-a created
pod/atelier-b created
pod/atelier-a condition met
pod/atelier-b condition met
```

Read each one's note, then the volume's full tree, with a throwaway Pod that
mounts it at the root (`--rm` deletes it at the end):

```bash
for a in a b; do kubectl exec atelier-$a -n essai-stock -- cat /travail/note; done; kubectl run inventaire --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-stock --restart=Never --rm -i --quiet --overrides='{"spec":{"containers":[{"name":"inventaire","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","ls -R /tout"],"volumeMounts":[{"name":"v","mountPath":"/tout"}]}],"volumes":[{"name":"v","persistentVolumeClaim":{"claimName":"reserve"}}]}}'
```

```text
ecrit par atelier-a
ecrit par atelier-b
/tout:
atelier-a
atelier-b

/tout/atelier-a:
note

/tout/atelier-b:
note
```

Each Pod only sees its own directory, but both are on the same volume. The
subdirectories were created at the first mount. The two Pods share a
`ReadWriteOnce` PV because they run on the same node: this mode limits the
volume to one node, not to one Pod.

## 🔏 Exercise 4: a read-only mount

Create a Pod that mounts the volume read-only, then reads a note and tries to
write (`écriture` means "write"):

```bash
cat <<YAML | kubectl apply -n essai-stock -f -
apiVersion: v1
kind: Pod
metadata:
  name: lecteur
spec:
  containers:
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      volumeMounts:
        - {name: v, mountPath: /lecture, readOnly: true}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: reserve, readOnly: true}
YAML
kubectl wait --for=condition=Ready pod/lecteur -n essai-stock --timeout=120s; kubectl exec lecteur -n essai-stock -- cat /lecture/atelier-a/note; kubectl exec lecteur -n essai-stock -- sh -c 'echo essai > /lecture/x'; echo "écriture : code $?"
```

```text
pod/lecteur created
pod/lecteur condition met
ecrit par atelier-a
sh: line 0: can't create /lecture/x: Read-only file system
command terminated with exit code 1
écriture : code 1
```

Reading works, writing is refused by the kernel (`Read-only file system`). A
Pod that only needs to read must not be able to damage the others' data.

## 🗑️ Exercise 5: delete a PVC still in use

Delete the PVC while three Pods use it:

```bash
kubectl delete pvc reserve -n essai-stock --wait=false; sleep 3; kubectl get pvc reserve -n essai-stock; kubectl get pvc reserve -n essai-stock -o jsonpath='{.metadata.finalizers}{"\n"}'
```

```text
persistentvolumeclaim "reserve" deleted from essai-stock namespace
NAME      STATUS        VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
reserve   Terminating   pv-lent   2Gi        RWO            essai          <unset>                 11s
["kubernetes.io/pvc-protection"]
```

The PVC stays in `Terminating`, held by the `kubernetes.io/pvc-protection`
finalizer: Kubernetes does not pull a volume from under a Pod that uses it.
Delete the Pods:

```bash
kubectl delete pod atelier-a atelier-b lecteur -n essai-stock --wait=true; sleep 3; kubectl get pvc -n essai-stock; kubectl get pv pv-lent
```

```text
pod "atelier-a" deleted from essai-stock namespace
pod "atelier-b" deleted from essai-stock namespace
pod "lecteur" deleted from essai-stock namespace
No resources found in essai-stock namespace.
NAME      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS     CLAIM                 STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
pv-lent   2Gi        RWO            Retain           Released   essai-stock/reserve   essai          <unset>                          45s
```

Once the Pods are gone, the PVC has disappeared. The PV has moved to
`Released`: its `Retain` policy keeps the data, but it will not bind to a new
claim. You must examine it, then delete it or put it back into service by
hand.

## 🧹 Clean-up

Delete the namespace and the two PVs, then erase their directories on the
worker. The PV is in `Retain`: deleting the PV does not touch the files.

```bash
kubectl delete namespace essai-stock; kubectl delete pv pv-rapide pv-lent; ssh -o StrictHostKeyChecking=no k8s-w1.lab sudo rm -rf /tmp/essai-stock-rapide /tmp/essai-stock-lent; echo "ssh : code $?"
```

```text
namespace "essai-stock" deleted
persistentvolume "pv-rapide" deleted
persistentvolume "pv-lent" deleted
Warning: Permanently added 'k8s-w1.lab' (ED25519) to the list of known hosts.
ssh : code 0
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-pv-pvc-storageclass
dsoxlab check cka-pv-pvc-storageclass
```

```text
╭─ Result: cka-pv-pvc-storageclass ──╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/11 tests  │
╰────────────────────────────────────╯
```

0 out of 11: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a PV, a claim that binds to it, and a Pod
whose data survives its deletion.

```bash
dsoxlab run cka-pv-pvc-storageclass
dsoxlab challenge cka-pv-pvc-storageclass
```
