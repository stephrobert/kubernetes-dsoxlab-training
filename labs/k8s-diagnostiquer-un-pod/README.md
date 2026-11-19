# Diagnose two failing Pods

A **Pod** is the smallest thing Kubernetes runs: one or more containers that
live together. In this course, you create Pods in two ways, you learn to
observe them, then you diagnose the two most common failures: an image that
cannot be found and a program that stops in a loop.

You work in a scratch namespace, `essai-pods`. The challenge will ask you to
diagnose and repair two other Pods: you will do it on your own, at the end.

Related page: [Kubernetes Pods: create, observe and diagnose](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/pods/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-diagnostiquer-un-pod
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: create a Pod in one command

Create the scratch namespace, then a Pod `accueil` that runs nginx:

```bash
kubectl create namespace essai-pods
kubectl run accueil \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-pods
kubectl wait --for=condition=Ready pod/accueil -n essai-pods --timeout=90s
kubectl get pods -n essai-pods
```

```text
namespace/essai-pods created
pod/accueil created
pod/accueil condition met
NAME      READY   STATUS    RESTARTS   AGE
accueil   1/1     Running   0          1s
```

`1/1 Running` with `0` restarts: this is the state of a healthy Pod. `READY`
counts the ready containers, `RESTARTS` the restarts.

## 📚 Exercise 2: write a Pod's manifest

kubectl can write a Pod's YAML file for you, without creating anything, with
`--dry-run=client -o yaml`:

```bash
kubectl run fiche \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-pods --dry-run=client -o yaml
```

```text
apiVersion: v1
kind: Pod
metadata:
  labels:
    run: fiche
  name: fiche
  namespace: essai-pods
spec:
  containers:
  - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
    name: fiche
    resources: {}
  dnsPolicy: ClusterFirst
  restartPolicy: Always
status: {}
```

It is a good starting point. Now write your own manifest in `~/fiche.yaml`,
then create the Pod from it:

```bash
cat > ~/fiche.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: fiche
  namespace: essai-pods
  labels:
    app: fiche
spec:
  restartPolicy: Always
  containers:
    - name: nginx
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      ports:
        - containerPort: 80
EOF
kubectl apply -f ~/fiche.yaml
kubectl wait --for=condition=Ready pod/fiche -n essai-pods --timeout=90s
```

```text
pod/fiche created
pod/fiche condition met
```

A file like this one is kept and shared: it is how a team works. The command
of exercise 1 is rather for trying things out.

## 📚 Exercise 3: observe a Pod

Four commands are always used in this order, from the lightest to the most
intrusive. First, where the Pod stands:

```bash
kubectl get pod accueil -n essai-pods -o wide
```

```text
NAME      READY   STATUS    RESTARTS   AGE   IP            NODE                     NOMINATED NODE   READINESS GATES
accueil   1/1     Running   0          2s    10.244.0.15   boutique-control-plane   <none>           <none>
```

`-o wide` adds the Pod's address and the node it runs on. Then, what
Kubernetes did for it, at the end of `describe`:

```bash
kubectl describe pod accueil -n essai-pods | sed -n '/^Events:/,$p'
```

```text
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  2s    default-scheduler  Successfully assigned essai-pods/accueil to boutique-control-plane
  Normal  Pulled     1s    kubelet            spec.containers{accueil}: Container image "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb" already present on machine and can be accessed by the pod
  Normal  Created    1s    kubelet            spec.containers{accueil}: Container created
  Normal  Started    1s    kubelet            spec.containers{accueil}: Container started
```

The events tell the steps in order: placement on a node, image already there,
container created, then started. Next, what the application wrote, and
finally a command run **inside** the container:

```bash
kubectl logs accueil -n essai-pods --tail=3
kubectl exec accueil -n essai-pods -- hostname
```

```text
2026/11/19 11:38:42 [notice] 1#1: start worker processes
2026/11/19 11:38:42 [notice] 1#1: start worker process 35
2026/11/19 11:38:42 [notice] 1#1: start worker process 36
accueil
```

`kubectl exec` runs the `hostname` command in the container, which answers
with the Pod's name.

## 📚 Exercise 4: read a Pod's phase

The **phase** sums up in one word where a Pod stands: `Pending` (not started
yet), `Running`, `Succeeded` or `Failed` (finished).

```bash
kubectl get pod accueil -n essai-pods -o jsonpath='{.status.phase}{"\n"}'
```

```text
Running
```

## 📚 Exercise 5: diagnose an image that cannot be found

Create a Pod that asks for an nginx version that does not exist, then wait a
little:

```bash
kubectl run mauvais-tag --image=nginx:9.9.9 -n essai-pods
sleep 20
kubectl get pod mauvais-tag -n essai-pods
```

```text
pod/mauvais-tag created
NAME          READY   STATUS             RESTARTS   AGE
mauvais-tag   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff`: Kubernetes cannot download the image, and it waits longer
and longer between two tries. The cause is in the warnings of `describe`:

```bash
kubectl describe pod mauvais-tag -n essai-pods | grep -E 'Warning|Status:'
```

```text
Status:           Pending
  Warning  Failed     19s               kubelet            spec.containers{mauvais-tag}: Error: ImagePullBackOff
  Warning  Failed     6s (x2 over 19s)  kubelet            spec.containers{mauvais-tag}: Failed to pull image "nginx:9.9.9": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:9.9.9": failed to resolve reference "docker.io/library/nginx:9.9.9": docker.io/library/nginx:9.9.9: not found
  Warning  Failed     6s (x2 over 19s)  kubelet            spec.containers{mauvais-tag}: Error: ErrImagePull
```

`nginx:9.9.9: not found`: this version does not exist. The Pod stays in the
`Pending` phase, since its container never started.

## 📚 Exercise 6: diagnose a container that crashes

Create a Pod whose program stops right away with code `2`:

```bash
kubectl run chute \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c 'echo "je tombe"; exit 2'
sleep 45
kubectl get pod chute -n essai-pods
```

```text
pod/chute created
NAME    READY   STATUS   RESTARTS      AGE
chute   0/1     Error    3 (33s ago)   45s
```

Kubernetes restarts the container after each stop: `RESTARTS` is already 3.
Depending on the moment, `STATUS` shows `Error`, `CrashLoopBackOff` or
`Running`. The exit code of the last stop is stored in the Pod's state:

```bash
kubectl get pod chute -n essai-pods -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
kubectl get pod chute -n essai-pods -o jsonpath='{.status.phase}{"\n"}'
```

```text
2
Running
```

Code `2` is indeed the program's. Notice that the phase stays `Running`, while
the container crashes in a loop: the phase alone is not enough to judge a Pod.
Look at `STATUS` and `RESTARTS` too.

## 📚 Exercise 7: see what `restartPolicy` does

`restartPolicy` tells Kubernetes what to do when a container stops. By default
(`Always`), it always restarts it. With `Never`, it never restarts it. Create
two Pods that are never restarted, one that succeeds and one that fails:

```bash
kubectl run reussit --restart=Never \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c 'echo ok; exit 0'
kubectl run echoue --restart=Never \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c 'echo ko; exit 1'
sleep 15
kubectl get pods reussit echoue -n essai-pods
```

```text
pod/reussit created
pod/echoue created
NAME      READY   STATUS      RESTARTS   AGE
reussit   0/1     Completed   0          15s
echoue    0/1     Error       0          15s
```

`reussit` is `Completed` (code 0) and `echoue` is `Error` (code 1). Neither
was restarted: `RESTARTS` stays at 0.

## 📚 Exercise 8: see that a lone Pod is not recreated

A Pod created directly, like `accueil`, is watched by nobody. Delete it:

```bash
kubectl delete pod accueil -n essai-pods
kubectl get pods -n essai-pods
```

```text
pod "accueil" deleted from essai-pods namespace
NAME          READY   STATUS             RESTARTS      AGE
chute         0/1     Error              3 (49s ago)   61s
echoue        0/1     Error              0             16s
fiche         1/1     Running            0             82s
mauvais-tag   0/1     ImagePullBackOff   0             81s
reussit       0/1     Completed          0             16s
```

`accueil` does not come back: no controller was asked to keep one. In
practice, you have your Pods managed by a Deployment, which recreates them.

## 🧹 Clean up

Delete the scratch namespace, with all its Pods, and the manifest file:

```bash
kubectl delete namespace essai-pods
rm ~/fiche.yaml
```

```text
namespace "essai-pods" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-diagnostiquer-un-pod
dsoxlab check k8s-diagnostiquer-un-pod
```

```text
╭─ Result: k8s-diagnostiquer-un-pod ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests   │
╰────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: diagnose the two failing Pods of the
`pods-en-panne` namespace, then repair them, each in the right way.

```bash
dsoxlab run k8s-diagnostiquer-un-pod
dsoxlab challenge k8s-diagnostiquer-un-pod
```
