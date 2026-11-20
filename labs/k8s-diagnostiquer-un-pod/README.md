# Diagnose two failing Pods

A **Pod** is the smallest thing Kubernetes runs: one or more containers that
live together. The lesson shows how to create a Pod, observe it, and recognise
an image that cannot be found or a program that stops in a loop. This course
makes you **repair** these Pods. Once created, a Pod can hardly be changed:
you see what changes in place, what the API refuses, and how to recreate a
Pod under the same name. You end with a Pod that no node accepts.

You work in a scratch namespace, `essai-pods`. The challenge will ask you to
diagnose and repair two other Pods: you will do it on your own, at the end.

Related page: [Kubernetes Pods: create, observe and diagnose](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/pods/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-diagnostiquer-un-pod
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` runs there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: record the waiting reason of a Pod

Create the scratch namespace and an `apercu` Pod that asks for a nginx version
that does not exist:

```bash
kubectl create namespace essai-pods
kubectl run apercu --image=nginx:9.9 -n essai-pods
```

```text
namespace/essai-pods created
pod/apercu created
```

Wait about twenty seconds, then read the reason in two ways: the `STATUS`
column, and the exact field of the container state, that `jsonpath` extracts
on its own.

```bash
kubectl get pod apercu -n essai-pods
kubectl get pod apercu -n essai-pods -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}{"\n"}'
```

```text
NAME     READY   STATUS             RESTARTS   AGE
apercu   0/1     ImagePullBackOff   0          20s
ImagePullBackOff
```

Depending on the moment, you will read `ErrImagePull` or `ImagePullBackOff`:
Kubernetes retries with growing intervals. Also note the **UID** of the Pod,
the unique identifier Kubernetes gave it when it was created:

```bash
kubectl get pod apercu -n essai-pods -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
d378b6aa-f14b-4a85-8de2-1b30e58b62a5
```

## 📚 Exercise 2: fix the image of a Pod without recreating it

The image of a container is one of the few fields you can change on an
existing Pod. `kubectl set image` needs the name of the **container**, not the
name of the Pod. With `kubectl run`, both have the same name, but check it:

```bash
kubectl describe pod apercu -n essai-pods | grep -A1 "^Containers:"
```

```text
Containers:
  apercu:
```

Change the image, wait until the Pod is ready, then read its UID again:

```bash
kubectl set image pod/apercu apercu=nginx:1.30.5 -n essai-pods
kubectl wait --for=condition=Ready pod/apercu -n essai-pods --timeout=120s
kubectl get pod apercu -n essai-pods
kubectl get pod apercu -n essai-pods -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
pod/apercu image updated
pod/apercu condition met
NAME     READY   STATUS    RESTARTS   AGE
apercu   1/1     Running   0          20s
d378b6aa-f14b-4a85-8de2-1b30e58b62a5
```

Same UID as in exercise 1: it is the same Pod, repaired in place. Its age
(`AGE`) did not go back to zero.

## 📚 Exercise 3: see the API refuse a new command

Create a `calcul` Pod whose program stops on an error, with code 4:

```bash
kubectl run calcul \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c "echo calcul: division par zéro >&2; exit 4"
```

```text
pod/calcul created
```

Fifteen seconds later, it has already restarted twice:

```bash
kubectl get pod calcul -n essai-pods
```

```text
NAME     READY   STATUS   RESTARTS      AGE
calcul   0/1     Error    2 (14s ago)   15s
```

Save the Pod's manifest to a file, then replace its command with a one-hour
wait:

```bash
kubectl get pod calcul -n essai-pods -o yaml > ~/essai-calcul.yaml
sed -i "s|echo calcul: division par zéro >&2; exit 4|sleep 3600|" ~/essai-calcul.yaml
grep -n -A3 "args:" ~/essai-calcul.yaml
```

```text
14:  - args:
15-    - sh
16-    - -c
17-    - 'sleep 3600'
```

Now try to send this new command to the existing Pod. `kubectl replace`
replaces the object in the cluster with the one you give it:

```bash
kubectl get pod calcul -n essai-pods -o yaml \
  | sed "s|echo calcul: division par zéro >&2; exit 4|sleep 3600|" \
  | kubectl replace -f -
```

```text
The Pod "calcul" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`,`spec.initContainers[*].image`,`spec.activeDeadlineSeconds`,`spec.tolerations` (only additions to existing tolerations),`spec.terminationGracePeriodSeconds` (allow it to be set to 1 if it was previously negative)
```

The API refuses, and its answer gives the full list of what can change on an
existing Pod: the images, a delay, tolerations. The command is not part of it.
This command reads the Pod right before sending it: a file read earlier could
give another error, `Conflict`, if the Pod restarted in the meantime.

## 📚 Exercise 4: recreate the Pod under the same name

To change the command, you must delete the Pod and recreate it.
`kubectl replace --force` does both, from the file fixed in exercise 3. Note
the UID before:

```bash
kubectl get pod calcul -n essai-pods -o jsonpath='{.metadata.uid}{"\n"}'
kubectl replace --force -f ~/essai-calcul.yaml
kubectl wait --for=condition=Ready pod/calcul -n essai-pods --timeout=120s
kubectl get pod calcul -n essai-pods
kubectl get pod calcul -n essai-pods -o jsonpath='{.metadata.uid} {.spec.containers[0].args}{"\n"}'
```

```text
58ba8d33-d3de-453c-b748-dc3b80d96d04
pod "calcul" deleted from essai-pods namespace
pod/calcul replaced
pod/calcul condition met
NAME     READY   STATUS    RESTARTS   AGE
calcul   1/1     Running   0          0s
b8137c1f-8559-4d01-ae67-d660b3304b74 ["sh","-c","sleep 3600"]
```

The Pod has the same name, but it is another object: new UID, age `0s`, no
restart. The file came from `kubectl get -o yaml` and still held the old UID,
the `resourceVersion` and a whole `status` block: `replace --force` ignores
them when it recreates. Compare with exercise 2: a fixed image keeps the Pod,
a fixed command replaces it.

## 📚 Exercise 5: a Pod that no node accepts

The lesson mentions a third failure: the Pod that stays `Pending`. Write a Pod
that reserves 16 processors:

```bash
cat > ~/essai-gourmand.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: gourmand
  namespace: essai-pods
spec:
  containers:
    - name: gourmand
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      resources:
        requests:
          cpu: "16"
EOF
kubectl apply -f ~/essai-gourmand.yaml
```

```text
pod/gourmand created
```

The `requests` field says what the Pod reserves on a node. Look at where it
stands, then read its events:

```bash
kubectl get pod gourmand -n essai-pods
kubectl describe pod gourmand -n essai-pods | sed -n '/^Events:/,$p'
```

```text
NAME       READY   STATUS    RESTARTS   AGE
gourmand   0/1     Pending   0          5s
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  6s    default-scheduler  0/1 nodes are available: 1 Insufficient cpu. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

Here, no container exists: no image to pull, no log to read. It is the
**scheduler**, which picks the node of every Pod, that explains its refusal:
`Insufficient cpu`. Check what the node offers:

```bash
kubectl get nodes -o custom-columns=NOM:.metadata.name,CPU:.status.allocatable.cpu
```

```text
NOM                      CPU
boutique-control-plane   2
```

Two processors, for a request of sixteen: the Pod will stay `Pending` as long
as its request does not go down or no bigger node arrives.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace,
with its three Pods, and the two files.

```bash
kubectl delete namespace essai-pods
rm ~/essai-calcul.yaml ~/essai-gourmand.yaml
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
