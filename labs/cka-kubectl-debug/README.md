# Get inside a container with no shell using kubectl debug

Many production images have **no shell**: a single binary, and nothing else.
It is safer, but `kubectl exec` then has nothing to start inside.
`kubectl debug` answers that problem: it adds an **ephemeral container** to the
Pod, which brings its own tools, without restarting the Pod. In this course,
you hit a container with no shell, you add an ephemeral container to it, first
blind then able to see its processes, you check that the Pod was not touched,
then you debug a node.

You work in a scratch namespace, `essai-debug`, with a `muet` ("mute") Pod
built on the Kubernetes `pause` image, which has no shell. The challenge is
about another application, in another namespace: you will visit it on your
own, at the end.

Related page: [Debug an application](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-kubectl-debug
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a container with no shell

Create the scratch namespace and the `muet` Pod, on the `pause` image:

```bash
kubectl create namespace essai-debug
kubectl run muet --image=registry.k8s.io/pause:3.10.2@sha256:f548e0e8e3dc1896ca956272154dde3314e8cc4fde0a57577ee9fa1c63f5baf4 -n essai-debug && kubectl wait --for=condition=Ready pod/muet -n essai-debug --timeout=120s
```

```text
namespace/essai-debug created
pod/muet created
pod/muet condition met
```

Try to run a command in it (`cut` shortens the message):

```bash
kubectl exec muet -n essai-debug -- sh -c 'ps' 2>&1 | cut -c1-160
```

```text
error: Internal error occurred: Internal error occurred: error executing command in container: failed to start exec "ea6b7ed96717a7
```

Failure: there is no `sh` in this image, so nothing to start. The logs say
nothing either ("fin des logs" means "end of logs"):

```bash
kubectl logs muet -n essai-debug; echo '(fin des logs)'
```

```text
(fin des logs)
```

Note the Pod's unique identifier (uid) and its number of restarts
(`redemarrages`), to compare them later:

```bash
kubectl get pod muet -n essai-debug -o jsonpath='uid={.metadata.uid} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'
```

```text
uid=1a5c8792-4109-4dbe-8b0d-12da46f510cc redemarrages=0
```

## 📚 Exercise 2: an ephemeral container that only sees itself

`kubectl debug` adds to the Pod an ephemeral container named `regard`
("look", `-c`), on an image that has a shell and `ps` (busybox). Its command
lists the processes, then sleeps to stay alive:

```bash
kubectl debug muet -n essai-debug -c regard --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -- sh -c 'ps; sleep 3600'
```

The command prints nothing. Read what the ephemeral container wrote:

```bash
sleep 8; kubectl logs muet -n essai-debug -c regard
```

```text
PID   USER     TIME  COMMAND
    1 root      0:00 sh -c ps; sleep 3600
    7 root      0:00 ps
```

The ephemeral container only sees its own processes. By default, each
container of a Pod has its own process space: the one of `muet` stays
invisible.

## 📚 Exercise 3: share the processes with --target

`--target=muet` asks the ephemeral container to share the process space of the
`muet` container. Add a second ephemeral container, `loupe` ("magnifying
glass"):

```bash
kubectl debug muet -n essai-debug -c loupe --target=muet --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -- sh -c 'ps; sleep 3600'
```

```text
Targeting container "muet". If you don't see processes from this container it may be because the container runtime doesn't support this feature.
```

```bash
sleep 8; kubectl logs muet -n essai-debug -c loupe
```

```text
PID   USER     TIME  COMMAND
    1 65535     0:00 /pause
   13 root      0:00 sh -c ps; sleep 3600
   19 root      0:00 ps
```

This time, the application's `/pause` process shows up, with number 1.
Through `/proc/1/`, `loupe` can even read the filesystem of `muet` and the
command line of its process. `kubectl exec` works in `loupe`, which has a
shell:

```bash
kubectl exec muet -n essai-debug -c loupe -- sh -c 'ls /proc/1/root/ | head -5; cat /proc/1/cmdline; echo'
```

```text
dev
etc
pause
proc
sys
/pause 
```

The `pause` binary is indeed alone at the root of the image.

## 📚 Exercise 4: the Pod was not created again

Read the uid, the restarts, and the list of ephemeral containers again
("ephemere" means "ephemeral", "cible" means "target"):

```bash
kubectl get pod muet -n essai-debug -o jsonpath='uid={.metadata.uid} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}{range .spec.ephemeralContainers[*]}ephemere {.name} cible={.targetContainerName}{"\n"}{end}'
kubectl get pod muet -n essai-debug
```

```text
uid=1a5c8792-4109-4dbe-8b0d-12da46f510cc redemarrages=0
ephemere regard cible=
ephemere loupe cible=muet
NAME   READY   STATUS    RESTARTS   AGE
muet   1/1     Running   0          18s
```

Same uid, no restart: it is the same Pod. Both ephemeral containers are listed
in `spec.ephemeralContainers`, and only `loupe` has a target. `READY 1/1` does
not count ephemeral containers. Try to remove one:

```bash
kubectl patch pod muet -n essai-debug --subresource ephemeralcontainers --type=json -p '[{"op":"remove","path":"/spec/ephemeralContainers/0"}]' 2>&1 | head -1 | cut -c1-160
```

```text
The Pod "muet" is invalid: spec.ephemeralContainers: Forbidden: existing ephemeral containers "regard" may not be removed
```

Refused: an ephemeral container cannot be removed. It stays attached to the
Pod until the Pod is deleted.

## 📚 Exercise 5: debug a node

`kubectl debug node/<node>` starts a debugging Pod **on a node**, with the
node's filesystem mounted in `/host`:

```bash
kubectl debug node/k8s-w1.lab -n essai-debug --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -- sh -c 'cat /host/etc/hostname; ls /host/var/log/pods | head -3' 2>&1 | grep -v -i 'warning'
```

```text
Creating debugging pod node-debugger-k8s-w1.lab-vctct with container debugger on node k8s-w1.lab.
```

Look at where it runs, what it shares with the node, and what it read:

```bash
sleep 10; P=$(kubectl get pods -n essai-debug -o name | grep node-debugger | head -1); kubectl get $P -n essai-debug -o jsonpath='noeud={.spec.nodeName} hostPID={.spec.hostPID} hostNetwork={.spec.hostNetwork}{"\n"}'; kubectl logs $P -n essai-debug
```

```text
noeud=k8s-w1.lab hostPID=true hostNetwork=true
k8s-w1.lab
calico-system_calico-node-hgw4d_451810c1-b102-4623-8de3-48544409830b
calico-system_csi-node-driver-lh854_fd4423c9-9020-4461-8993-0d327ba326ce
essai-debug_muet_1a5c8792-4109-4dbe-8b0d-12da46f510cc
```

The Pod runs on `k8s-w1.lab`, shares the node's processes (`hostPID`) and
network (`hostNetwork`), and reads its files: its name, and the logs of the
Pods it hosts, `muet` among them. It is powerful: keep this move for
troubleshooting a node.

## 🧹 Clean up

Delete the scratch namespace. It is the only way to remove the ephemeral
containers, and the node debugging Pod goes with it:

```bash
kubectl delete namespace essai-debug
```

```text
namespace "essai-debug" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-kubectl-debug
dsoxlab check cka-kubectl-debug
```

```text
╭──── Result: cka-kubectl-debug ────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests  │
╰───────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another application with no shell, whose
processes you must list from the inside with an ephemeral container.

```bash
dsoxlab run cka-kubectl-debug
dsoxlab challenge cka-kubectl-debug
```
