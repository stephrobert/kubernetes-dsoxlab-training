# Let one container read what another writes

Two containers of the same Pod share the network, but not their files: each
one sees the filesystem of its own image. To pass files from one to the other,
you give them a shared **volume**. In this course, you see this separation, you
see that you cannot add a volume to a running Pod, you share one directory and
only one, you mount it read-only, you see how long an `emptyDir` volume lives,
and you put one in memory.

You work in a scratch namespace, `essai-volumes`, with an `atelier`
("workshop") Pod and its `ecrivain` ("writer") and `relecteur` ("reader")
containers. The challenge will ask you to repair another Pod, in another
namespace: you will do it on your own, at the end.

Related page: [Application volumes](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/application-volumes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-volumes-partage-entre-conteneurs
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: same Pod, separate files

Create the scratch namespace and an `atelier` Pod with two containers,
**without** a volume. The writer creates `/partage/note.txt`, the reader only
waits:

```bash
kubectl create namespace essai-volumes
cat > ~/atelier-sans-volume.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: atelier
spec:
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "mkdir -p /partage; echo note de l ecrivain > /partage/note.txt; sleep 3600"]
    - name: relecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
YAML
kubectl apply -n essai-volumes -f ~/atelier-sans-volume.yaml && kubectl wait --for=condition=Ready pod/atelier -n essai-volumes --timeout=120s
```

```text
namespace/essai-volumes created
pod/atelier created
pod/atelier condition met
```

Read the file from each of the two containers (`-c` picks the container):

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- cat /partage/note.txt; kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
note de l ecrivain
cat: can't open '/partage/note.txt': No such file or directory
command terminated with exit code 1
```

The writer sees its file ("the writer's note"), the reader does not. Yet they
do share the network: they have the same IP address.

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- hostname -i; kubectl exec atelier -n essai-volumes -c relecteur -- hostname -i
```

```text
10.244.38.116
10.244.38.116
```

## 📚 Exercise 2: you do not change the volumes of a running Pod

Write the version with a volume. A volume is declared at **two** levels:

- once for the Pod, under `spec.volumes`: here an `emptyDir`, an empty
  directory created with the Pod;
- then in each container that must see it, under `volumeMounts`, with its
  path.

The reader mounts it read-only (`readOnly: true`). The writer also writes a
draft **outside** the volume, in `/ailleurs` ("elsewhere"):

```bash
cat > ~/atelier.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: atelier
spec:
  volumes:
    - name: partage
      emptyDir: {}
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo note de l ecrivain > /partage/note.txt; mkdir -p /ailleurs; echo brouillon prive > /ailleurs/brouillon.txt; sleep 3600"]
      volumeMounts:
        - name: partage
          mountPath: /partage
    - name: relecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: partage
          mountPath: /partage
          readOnly: true
YAML
kubectl apply -n essai-volumes -f ~/atelier.yaml 2>&1 | head -1 | cut -c1-160
```

```text
The Pod "atelier" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`,`spec.initContainers[*].image`,`spec.acti
```

Refused: you can change almost nothing of an existing Pod, and certainly not
its volumes (`head` and `cut` shorten a very long message here). You must
delete the Pod and create it again:

```bash
kubectl delete pod atelier -n essai-volumes --wait=true && kubectl apply -n essai-volumes -f ~/atelier.yaml && kubectl wait --for=condition=Ready pod/atelier -n essai-volumes --timeout=120s
```

```text
pod "atelier" deleted from essai-volumes namespace
pod/atelier created
pod/atelier condition met
```

## 📚 Exercise 3: what crosses, and what does not

The reader now sees the note:

```bash
kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
note de l ecrivain
```

And the draft, written outside the volume?

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- cat /ailleurs/brouillon.txt; kubectl exec atelier -n essai-volumes -c relecteur -- cat /ailleurs/brouillon.txt
```

```text
brouillon prive
cat: can't open '/ailleurs/brouillon.txt': No such file or directory
command terminated with exit code 1
```

Only the mounted directory is shared. Everything else in each container stays
its own. That is why you mount the volume where the files to exchange go, and
no higher: on `/`, it would share everything. Here is the mount, seen from the
reader:

```bash
kubectl exec atelier -n essai-volumes -c relecteur -- sh -c 'mount | grep /partage'
```

```text
/dev/vda1 on /partage type ext4 (ro,relatime,discard,errors=remount-ro,commit=30)
```

`ro`: read-only. The volume is a directory on the node's disk (`/dev/vda1`),
mounted into the container.

## 📚 Exercise 4: a read-only mount

The reader tries to write into the volume:

```bash
kubectl exec atelier -n essai-volumes -c relecteur -- sh -c 'echo correction > /partage/note.txt'
```

```text
sh: line 0: can't create /partage/note.txt: Read-only file system
command terminated with exit code 1
```

Refused. The writer can still write, and the reader sees the addition:

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- sh -c 'echo ajout de l ecrivain >> /partage/note.txt'; kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
note de l ecrivain
ajout de l ecrivain
```

## 📚 Exercise 5: the life of an emptyDir

How long does an `emptyDir` live? Create a `compteur` Pod whose writer notes
its start time, waits 8 seconds, then stops. Kubernetes restarts it each time.
A reader stays up to read the volume:

```bash
cat <<'YAML' | kubectl apply -n essai-volumes -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur
spec:
  volumes:
    - name: partage
      emptyDir: {}
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo demarrage a $(date +%T) >> /partage/demarrages.txt; sleep 8"]
      volumeMounts:
        - name: partage
          mountPath: /partage
    - name: relecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: partage
          mountPath: /partage
YAML
```

```text
pod/compteur created
```

40 seconds later ("demarrage a" means "start at"):

```bash
sleep 40; kubectl get pod compteur -n essai-volumes; kubectl exec compteur -n essai-volumes -c relecteur -- cat /partage/demarrages.txt
```

```text
NAME       READY   STATUS     RESTARTS      AGE
compteur   1/2     NotReady   2 (24s ago)   40s
demarrage a 21:14:17
demarrage a 21:14:25
demarrage a 21:14:48
```

The writer restarted 2 times, and the file keeps one line per start: the volume
**survives a container restart**. Now delete the `atelier` Pod, then create it
again from the same file:

```bash
kubectl delete pod atelier -n essai-volumes --wait=true && kubectl apply -n essai-volumes -f ~/atelier.yaml && kubectl wait --for=condition=Ready pod/atelier -n essai-volumes --timeout=120s && kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
pod "atelier" deleted from essai-volumes namespace
pod/atelier created
pod/atelier condition met
note de l ecrivain
```

The `ajout de l ecrivain` line from exercise 4 is gone: an `emptyDir` **is born
and dies with its Pod**. It is there to pass files along, not to keep them.

## 📚 Exercise 6: an emptyDir in memory

An `emptyDir` can live in memory rather than on the node's disk:
`medium: Memory`. `sizeLimit` caps its size:

```bash
cat <<'YAML' | kubectl apply -n essai-volumes -f -
apiVersion: v1
kind: Pod
metadata:
  name: rapide
spec:
  volumes:
    - name: cache
      emptyDir:
        medium: Memory
        sizeLimit: 32Mi
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: cache
          mountPath: /cache
YAML
kubectl wait --for=condition=Ready pod/rapide -n essai-volumes --timeout=120s
```

```text
pod/rapide created
pod/rapide condition met
```

Compare the two volumes with `df`:

```bash
kubectl exec rapide -n essai-volumes -- df -h /cache
kubectl exec atelier -n essai-volumes -c ecrivain -- df -h /partage
```

```text
Filesystem                Size      Used Available Use% Mounted on
tmpfs                    32.0M         0     32.0M   0% /cache
Filesystem                Size      Used Available Use% Mounted on
/dev/vda1                18.3G      4.3G     14.0G  24% /partage
```

`/cache` is a `tmpfs` (a filesystem in memory) of 32 MB. `/partage` is on the
node's disk, whose space it shares.

## 🧹 Clean up

Delete the scratch namespace and the work files:

```bash
kubectl delete namespace essai-volumes; rm -f ~/atelier.yaml ~/atelier-sans-volume.yaml
```

```text
namespace "essai-volumes" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-volumes-partage-entre-conteneurs
dsoxlab check ckad-volumes-partage-entre-conteneurs
```

```text
╭─ Result: ckad-volumes-partage-entre-conteneurs ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                │
╰─────────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another Pod, whose reader does not find what
the producer writes. Share the right directory, and only that one.

```bash
dsoxlab run ckad-volumes-partage-entre-conteneurs
dsoxlab challenge ckad-volumes-partage-entre-conteneurs
```
