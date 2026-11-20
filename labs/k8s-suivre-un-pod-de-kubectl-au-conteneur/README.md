# Follow a Pod from kubectl to the container

When you create an application, several Kubernetes components work one after
the other before a container runs. Each one leaves a trace: an **event**, which
says what happened and who did it. In this course, you follow this path move by
move, as in the lesson:

- the **API server** receives and saves your request;
- the **controllers** create the missing objects (ReplicaSet, Pods);
- the **scheduler** picks a node for each Pod;
- the **kubelet** of the chosen node starts the container.

You work in a scratch namespace, `essai-trajet`, with a Deployment `trajet` of
three Pods. The challenge will ask you to record this path for another
application: you will do it on your own, at the end.

Related page: [Kubernetes architecture](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/architecture/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-suivre-un-pod-de-kubectl-au-conteneur
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`architecture` is running there, with one control plane and three workers, and
your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: create a Deployment of three Pods

Create the scratch namespace, then a Deployment of three Pods, and wait for
them to run:

```bash
kubectl create namespace essai-trajet
kubectl create deployment trajet \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  --replicas=3 -n essai-trajet
kubectl wait --for=condition=Available deployment/trajet -n essai-trajet --timeout=180s
```

```text
namespace/essai-trajet created
deployment.apps/trajet created
deployment.apps/trajet condition met
```

The `created` line means the API server accepted and saved your request. At
that moment, nothing runs yet. The `condition met` line only shows once the
three Pods run: the whole path took place between the two.

## 📚 Exercise 2: see which node each Pod runs on

```bash
kubectl get pods -n essai-trajet -o wide
```

```text
NAME                     READY   STATUS    RESTARTS   AGE   IP           NODE                   NOMINATED NODE   READINESS GATES
trajet-fb65d8867-5rx62   1/1     Running   0          18s   10.244.2.2   architecture-worker    <none>           <none>
trajet-fb65d8867-7x5hz   1/1     Running   0          18s   10.244.1.2   architecture-worker2   <none>           <none>
trajet-fb65d8867-nzjkn   1/1     Running   0          18s   10.244.3.2   architecture-worker3   <none>           <none>
```

The `NODE` column shows the node chosen for each Pod: the scheduler spread the
three Pods over the three workers. The `IP` column shows each Pod has its own
address. On your side, names and spread may differ.

## 📚 Exercise 3: read a Pod's events

Store the name of the first Pod in a variable, then show the end of its
`describe`, from the `Events:` line:

```bash
POD=$(kubectl get pods -n essai-trajet -o jsonpath='{.items[0].metadata.name}')
echo $POD
kubectl describe pod $POD -n essai-trajet | sed -n '/^Events:/,$p'
```

```text
trajet-fb65d8867-5rx62
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  18s   default-scheduler  Successfully assigned essai-trajet/trajet-fb65d8867-5rx62 to architecture-worker
  Normal  Pulling    17s   kubelet            spec.containers{nginx}: Pulling image "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
  Normal  Pulled     0s    kubelet            spec.containers{nginx}: Successfully pulled image "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb" in 16.7s (16.7s including waiting). Image size: 63638242 bytes.
  Normal  Created    0s    kubelet            spec.containers{nginx}: Container created
  Normal  Started    0s    kubelet            spec.containers{nginx}: Container started
```

Look at the `From` column, which says who did what:

- `Scheduled` comes from `default-scheduler`: it placed the Pod on
  `architecture-worker`;
- `Pulling`, `Pulled`, `Created` and `Started` come from `kubelet`: the one of
  `architecture-worker` downloaded the image, created the container, then
  started it.

## 📚 Exercise 4: read the ReplicaSet's events

The earlier steps, the creation of the Pods, are read on the ReplicaSet:

```bash
kubectl get rs -n essai-trajet
RS=$(kubectl get rs -n essai-trajet -o jsonpath='{.items[0].metadata.name}')
kubectl describe rs $RS -n essai-trajet \
  | grep -E '^(Name|Controlled By|Replicas|Pods Status):|SuccessfulCreate'
```

```text
NAME               DESIRED   CURRENT   READY   AGE
trajet-fb65d8867   3         3         3       18s
Name:           trajet-fb65d8867
Controlled By:  Deployment/trajet
Replicas:       3 current / 3 desired
Pods Status:    3 Running / 0 Waiting / 0 Succeeded / 0 Failed
  Normal  SuccessfulCreate  18s   replicaset-controller  Created pod: trajet-fb65d8867-7x5hz
  Normal  SuccessfulCreate  18s   replicaset-controller  Created pod: trajet-fb65d8867-nzjkn
  Normal  SuccessfulCreate  18s   replicaset-controller  Created pod: trajet-fb65d8867-5rx62
```

`Controlled By: Deployment/trajet`: this ReplicaSet belongs to the Deployment.
The three `SuccessfulCreate` lines, written by `replicaset-controller`, are the
creation of the three Pods.

## 📚 Exercise 5: see all the events, with their source

`kubectl get events -o wide` lists the events of the whole namespace. The
`SOURCE` column says which component wrote each one. The output is very wide,
here is its start:

```bash
kubectl get events -n essai-trajet -o wide --sort-by=.lastTimestamp | head -8
```

```text title="Excerpt of the output"
LAST SEEN   TYPE     REASON              OBJECT                        SUBOBJECT                SOURCE                          MESSAGE                                                                                                                                                                              FIRST SEEN   COUNT   NAME
18s         Normal   SuccessfulCreate    replicaset/trajet-fb65d8867                            replicaset-controller           Created pod: trajet-fb65d8867-7x5hz                                                                                                                                                  18s          1       trajet-fb65d8867.18e96d5a3c35bb4a
18s         Normal   Scheduled           pod/trajet-fb65d8867-nzjkn                             default-scheduler               Successfully assigned essai-trajet/trajet-fb65d8867-nzjkn to architecture-worker3                                                                                                    18s          1       trajet-fb65d8867-nzjkn.18e96d5a3fe8a4e4
18s         Normal   ScalingReplicaSet   deployment/trajet                                      deployment-controller           Scaled up replica set trajet-fb65d8867 from 0 to 3                                                                                                                                   18s          1       trajet.18e96d5a3b02c2d9
```

Three components show up: `deployment-controller` created the ReplicaSet,
`replicaset-controller` created the Pods, `default-scheduler` placed them.

## 📚 Exercise 6: delete a Pod and watch Kubernetes replace it

You asked for three Pods. Delete one:

```bash
POD=$(kubectl get pods -n essai-trajet -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD -n essai-trajet
sleep 5
kubectl get pods -n essai-trajet
```

```text
pod "trajet-fb65d8867-5rx62" deleted from essai-trajet namespace
NAME                     READY   STATUS    RESTARTS   AGE
trajet-fb65d8867-7x5hz   1/1     Running   0          25s
trajet-fb65d8867-mqvjk   1/1     Running   0          7s
trajet-fb65d8867-nzjkn   1/1     Running   0          25s
```

There are three Pods again. The deleted Pod did not come back: this is a
**new** Pod (`mqvjk`, 7 seconds). The ReplicaSet saw two Pods instead of three,
and created one. The events tell the rest:

```bash
kubectl get events -n essai-trajet --sort-by=.lastTimestamp | tail -6
```

```text
7s          Normal   Scheduled           pod/trajet-fb65d8867-mqvjk    Successfully assigned essai-trajet/trajet-fb65d8867-mqvjk to architecture-worker
7s          Normal   Created             pod/trajet-fb65d8867-5rx62    Container created
6s          Normal   Started             pod/trajet-fb65d8867-mqvjk    Container started
6s          Normal   Killing             pod/trajet-fb65d8867-5rx62    Stopping container nginx
6s          Normal   Created             pod/trajet-fb65d8867-mqvjk    Container created
6s          Normal   Pulled              pod/trajet-fb65d8867-mqvjk    Container image "nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb" already present on machine and can be accessed by the pod
```

The new Pod follows the same path: `Scheduled`, then `Created` and `Started`.
The image was already on the node (`already present on machine`): no download
this time. `Killing` is the stop of the deleted Pod's container.

Two lines need a careful reading. The `Created` line of `5rx62` is about the
old Pod, the one you deleted, not the new one. And the list is sorted to the
second: when several events fall in the same second, their display order is not
reliable. Here, the `Started` of `mqvjk` shows up before its `Created`. To
know the real order for a Pod, read its events with `kubectl describe pod`.

## 📚 Exercise 7: reach a Pod by its address

Each Pod has its own address, and any Pod can reach any other Pod directly.
Note a Pod's address:

```bash
kubectl get pods -n essai-trajet -o jsonpath='{.items[0].status.podIP}'; echo
```

```text
10.244.1.2
```

Start a temporary Pod and ask for the page at this address. Replace
`10.244.1.2` with the address you noted:

```bash
kubectl run test --rm -i --restart=Never -n essai-trajet \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  -- wget -qO- http://10.244.1.2
```

```text title="Excerpt of the output"
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
pod "test" deleted from essai-trajet namespace
```

nginx's page shows: the `test` Pod reached a Pod of the cluster by its address,
without configuring anything. Sometimes the page shows **twice**, with the line
`warning: couldn't attach to pod/test, falling back to streaming logs`: the Pod
finished before kubectl connected to it, and kubectl reads its output again.
It is not an error.

## 🧹 Clean up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-trajet
```

```text
namespace "essai-trajet" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```

```text
╭─ Result: k8s-suivre-un-pod-de-kubectl-au-conteneur ─╮
│  0 / 100 pts                                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                    │
╰─────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: create the challenge's application, then
record in its events who placed it, who started it, and on which node.

```bash
dsoxlab run k8s-suivre-un-pod-de-kubectl-au-conteneur
dsoxlab challenge k8s-suivre-un-pod-de-kubectl-au-conteneur
```
