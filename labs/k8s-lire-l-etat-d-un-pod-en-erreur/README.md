# Read the state of a failing Pod

When an application does not start, you first need to **understand why**,
before fixing anything. Four kubectl commands each answer one question, in
this order:

- `kubectl get`: **which** Pod is failing?
- `kubectl describe`: **why** is it failing?
- `kubectl logs`: **what did** the application write before stopping?
- `kubectl top`: **how much** does it use?

In this course, you create three small applications yourself in a scratch
namespace, `essai-panne`: one that works, one whose image does not exist, and
one that stops on an error. Then you diagnose them. The challenge will ask you
to diagnose other failures, in the `diagnostic` namespace: you will do it on
your own, at the end.

Related page: [kubectl get, describe, logs and top](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-get-describe-logs-top/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-lire-l-etat-d-un-pod-en-erreur
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab` is
running there, and your kubectl already targets it. The **metrics-server**
measuring tool, which `kubectl top` needs, is installed.

Create the scratch namespace and its three applications:

```bash
kubectl create namespace essai-panne
kubectl create deployment front \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-panne
kubectl create deployment cache --image=nginx:9.99 -n essai-panne
kubectl create deployment tache \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  -n essai-panne \
  -- sh -c 'echo "tache: lancement"; echo "erreur: fichier /etc/tache.conf introuvable" >&2; exit 3'
```

```text
namespace/essai-panne created
deployment.apps/front created
deployment.apps/cache created
deployment.apps/tache created
```

`front` is a web server that works. `cache` asks for nginx version `9.99`,
which does not exist. `tache` writes an error message, then stops with code
`3`. Wait a minute before going on, while Kubernetes tries to start them.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: spot the failing Pod

List the Pods of the namespace:

```bash
kubectl get pods -n essai-panne
```

```text
NAME                     READY   STATUS         RESTARTS      AGE
cache-6bcb8d84c5-4hhx5   0/1     ErrImagePull   0             61s
front-545fdfbcf8-8v4ph   1/1     Running        0             61s
tache-7794c9cf45-q4xzs   0/1     Error          3 (48s ago)   60s
```

Three columns are enough to spot problems:

- `READY`: `0/1` means no container of the Pod is ready;
- `STATUS`: `ErrImagePull` for `cache` (the image does not download), `Error`
  for `tache` (the program stopped on an error);
- `RESTARTS`: `tache` already restarted 3 times. A counter that goes up means
  the program starts then stops, in a loop.

To see one application only, filter on its label with `-l`:

```bash
kubectl get pods -n essai-panne -l app=front
```

```text
NAME                     READY   STATUS    RESTARTS   AGE
front-545fdfbcf8-8v4ph   1/1     Running   0          61s
```

## 📚 Exercise 2: show more columns, or a single value

The `-o wide` option adds columns, including the Pod's address and the node it
runs on:

```bash
kubectl get pods -n essai-panne -o wide
```

```text
NAME                     READY   STATUS         RESTARTS      AGE   IP            NODE                NOMINATED NODE   READINESS GATES
cache-6bcb8d84c5-4hhx5   0/1     ErrImagePull   0             61s   10.244.0.12   lab-control-plane   <none>           <none>
front-545fdfbcf8-8v4ph   1/1     Running        0             61s   10.244.0.11   lab-control-plane   <none>           <none>
tache-7794c9cf45-q4xzs   0/1     Error          3 (48s ago)   60s   10.244.0.13   lab-control-plane   <none>           <none>
```

The other way round, `-o jsonpath` shows a single value. Ask for the image of
the `cache` Pod:

```bash
kubectl get pods -n essai-panne -l app=cache -o jsonpath='{.items[0].spec.containers[0].image}'; echo
```

```text
nginx:9.99
```

The `; echo` adds the line break `jsonpath` does not print.

## 📚 Exercise 3: understand why `cache` does not start

`kubectl describe` shows everything Kubernetes knows about the Pod. The output
is long: `grep` keeps only the useful lines here. With `-l`, `describe` hides
the events, unless you add `--show-events=true`.

```bash
kubectl describe pod -n essai-panne -l app=cache --show-events=true \
  | grep -E "^(Name|Status):|Image:|State:|Reason:|Warning"
```

```text
Name:             cache-6bcb8d84c5-4hhx5
Status:           Pending
    Image:          nginx:9.99
    State:          Waiting
      Reason:       ErrImagePull
  Warning  Failed     20s (x3 over 60s)  kubelet            spec.containers{nginx}: Failed to pull image "nginx:9.99": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:9.99": failed to resolve reference "docker.io/library/nginx:9.99": docker.io/library/nginx:9.99: not found
  Warning  Failed     20s (x3 over 60s)  kubelet            spec.containers{nginx}: Error: ErrImagePull
  Warning  Failed     8s (x3 over 59s)   kubelet            spec.containers{nginx}: Error: ImagePullBackOff
```

Read in this order:

1. `State: Waiting` with `Reason: ErrImagePull`: the container is waiting, it
   never started;
2. the `Warning` lines give the cause: `nginx:9.99: not found`, this image
   version does not exist.

`(x3 over 60s)` means Kubernetes tried three times in 60 seconds.

## 📚 Exercise 4: understand why `tache` stops

For `tache`, the story is different: the container did start, then stopped.

```bash
kubectl describe pod -n essai-panne -l app=tache \
  | grep -E "State:|Reason:|Exit Code:|Restart Count:"
```

```text
    State:          Terminated
      Reason:       Error
      Exit Code:    3
    Last State:     Terminated
      Reason:       Error
      Exit Code:    3
    Restart Count:  3
```

`State: Terminated`: the container stopped. `Exit Code: 3` is the program's
exit code: any code other than 0 means a failure. `Last State` describes the
previous run, which stopped the same way. Kubernetes did its job: the problem
is in the program. To know why it stops, you have to read what it wrote
(exercise 6).

## 📚 Exercise 5: see all the warnings of the namespace

`describe` shows the events of a single Pod. `kubectl get events` shows those
of the whole namespace. Keep only the warnings:

```bash
kubectl get events -n essai-panne --field-selector type=Warning
```

```text
LAST SEEN   TYPE      REASON    OBJECT                       MESSAGE
20s         Warning   Failed    pod/cache-6bcb8d84c5-4hhx5   Failed to pull image "nginx:9.99": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:9.99": failed to resolve reference "docker.io/library/nginx:9.99": docker.io/library/nginx:9.99: not found
20s         Warning   Failed    pod/cache-6bcb8d84c5-4hhx5   Error: ErrImagePull
8s          Warning   Failed    pod/cache-6bcb8d84c5-4hhx5   Error: ImagePullBackOff
20s         Warning   BackOff   pod/tache-7794c9cf45-q4xzs   Back-off restarting failed container busybox in pod tache-7794c9cf45-q4xzs_essai-panne(2df306c3-14b0-43f1-9a5c-91459e6441f1)
```

In one command, you see both failures. `BackOff` means Kubernetes waits a
little before restarting `tache`, and waits longer after each failure.

## 📚 Exercise 6: read what the application wrote

`kubectl logs` shows what the program wrote. Read the logs of `tache`:

```bash
kubectl logs deployment/tache -n essai-panne
```

```text
erreur: fichier /etc/tache.conf introuvable
tache: lancement
```

There is the cause: a configuration file is missing. The two lines are not in
the order they were written: the normal message and the error message go
through two different channels, which kubectl mixes.

Now try the logs of `cache`:

```bash
kubectl logs deployment/cache -n essai-panne
```

```text
Error from server (BadRequest): container "nginx" in pod "cache-6bcb8d84c5-4hhx5" is waiting to start: image can't be pulled
```

There is no log: a container that never started wrote nothing. For it,
`describe` gave the answer.

The `--previous` option reads the logs of the previous run, the one that
crashed. On `front`, which never restarted, it finds nothing:

```bash
kubectl logs deployment/front -n essai-panne --previous
```

```text
Error from server (BadRequest): previous terminated container "nginx" in pod "front-545fdfbcf8-8v4ph" not found
```

This message means "no restart", so no crash to explain.

## 📚 Exercise 7: measure the consumption

`kubectl top` shows what the Pods use right now: processor (in thousandths of a
core, `m`) and memory (in `Mi`).

```bash
kubectl top pods -n essai-panne
```

```text
NAME                     CPU(cores)   MEMORY(bytes)
front-545fdfbcf8-8v4ph   0m           3Mi
```

Only `front` shows up: a Pod that does not run uses nothing, so it has no
measurement. `top` is not for finding a failing Pod, it is for spotting the one
that uses too much.

Rank the Pods of a busier namespace, `kube-system`, by memory:

```bash
kubectl top pods -n kube-system --sort-by=memory | head -4
```

```text
NAME                                        CPU(cores)   MEMORY(bytes)
kube-apiserver-lab-control-plane            35m          249Mi
kube-controller-manager-lab-control-plane   12m          77Mi
etcd-lab-control-plane                      19m          49Mi
```

The first of the list is the one that uses the most memory.

## 🧹 Clean up

Delete the scratch namespace. Its three applications go with it:

```bash
kubectl delete namespace essai-panne
```

```text
namespace "essai-panne" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-lire-l-etat-d-un-pod-en-erreur
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```

```text
╭─ Result: k8s-lire-l-etat-d-un-pod-en-erreur ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests             │
╰──────────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: diagnose the two failing applications of the
`diagnostic` namespace, and find the one that uses the most memory, without
fixing anything.

```bash
dsoxlab run k8s-lire-l-etat-d-un-pod-en-erreur
dsoxlab challenge k8s-lire-l-etat-d-un-pod-en-erreur
```
