# Open an application outside the cluster with a NodePort Service

A Service of type `ClusterIP` can only be reached from inside the cluster. For
a user outside to reach the application, the **NodePort** type also opens a
port on **every node** of the cluster. A request sent to that port, on any
node, reaches one of the Pods. The lesson creates a NodePort Service. This
course makes you reach it through every node, fix its port, and meet two
limits: a node port already taken, and `externalTrafficPolicy: Local`, which
closes the nodes that run no Pod.

You work in a scratch namespace, `essai-nodeport`, with a `vitrine`
application. The challenge will ask you to repair another NodePort Service:
you will do it on your own, at the end.

Related page: [Kubernetes Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-service-nodeport-reparer
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: the application, and the addresses of the nodes

Create the scratch namespace, then the `vitrine` application, in two Pods that
serve the text `vitrine` on port 8080:

```bash
kubectl create namespace essai-nodeport
cat <<'YAML' | kubectl apply -n essai-nodeport -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitrine
  template:
    metadata:
      labels:
        app: vitrine
    spec:
      terminationGracePeriodSeconds: 5
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo vitrine > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
YAML
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
```

```text
namespace/essai-nodeport created
deployment.apps/vitrine created
deployment "vitrine" successfully rolled out
```

The `terminationGracePeriodSeconds: 5` field shortens the stop of a Pod. To
stop a container, Kubernetes sends a stop signal to the main process, the one
with number 1. A process number 1 that has nothing planned for this signal
ignores it: here, that is the case of `httpd` as well as `sh`. Kubernetes then
waits for the set delay, 30 seconds by default, before cutting the container.
Measured on this cluster: 31 seconds with `exec httpd`, 32 without. The 5
second delay avoids that wait when a Pod goes away.

A NodePort is reached through the address of a node. These addresses are read
in the `INTERNAL-IP` column. The `awk` command only keeps three columns:

```bash
kubectl get nodes -o wide | awk '{print $1, $2, $6}' | column -t
```

```text
NAME        STATUS  INTERNAL-IP
k8s-cp.lab  Ready   10.10.50.11
k8s-w1.lab  Ready   10.10.50.12
```

## 📚 Exercise 2: a NodePort Service

`kubectl expose` creates the Service. The `--type=NodePort` option makes it a
NodePort:

```bash
kubectl expose deployment vitrine --type=NodePort --port=80 --target-port=8080 -n essai-nodeport
kubectl get service vitrine -n essai-nodeport
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0]}{"\n"}'
```

```text
service/vitrine exposed
NAME      TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.101.247.28   <none>        80:30275/TCP   0s
{"nodePort":30275,"port":80,"protocol":"TCP","targetPort":8080}
```

The `PORT(S)` column says `80:30275`. A NodePort Service has **three** ports:

- `port` (80): the port of the Service inside the cluster;
- `targetPort` (8080): the port of the container, where requests arrive;
- `nodePort` (30275): the port opened on **every node**. You did not pick it:
  Kubernetes drew it at random in its range, from 30000 to 32767.

## 📚 Exercise 3: reach the application through each node

Query the node port on both nodes. The `NP` variable takes the `nodePort`,
since it was drawn at random. The `sleep 3` gives the cluster time to open
this port on the nodes:

```bash
sleep 3; NP=$(kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

Both nodes answer. Now scale the application down to a single Pod, then look
at which node it runs on:

```bash
kubectl scale deployment vitrine --replicas=1 -n essai-nodeport
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
sleep 10; kubectl get pods -n essai-nodeport -o wide | awk '{print $1, $3, $7}' | column -t
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
NAME                      STATUS   NODE
vitrine-668ff869cd-68fq5  Running  k8s-cp.lab
```

The only Pod runs on `k8s-cp.lab`. Query both nodes again:

```bash
curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

`k8s-w1.lab` answers too, while it runs no `vitrine` Pod. The port is open on
**every** node, and each one passes the request on to the Pod, wherever it
runs.

## 📚 Exercise 4: pick the node port

A port drawn at random does not suit users: they need a fixed address. Set
the `nodePort` to `30095` with `kubectl patch`. The port is named by its
`port` (80), so that Kubernetes knows which one to change:

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":30095}]}}'
kubectl get service vitrine -n essai-nodeport
sleep 3; curl -s http://10.10.50.11:30095/
```

```text
service/vitrine patched
NAME      TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.101.247.28   <none>        80:30095/TCP   14s
vitrine
```

`80:30095`: the node port is now the one you picked.

## 📚 Exercise 5: a port outside the range

Try a node port easier to remember, `8080`:

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":8080}]}}'
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}{"\n"}'
```

```text
The Service "vitrine" is invalid: spec.ports[0].nodePort: Invalid value: 8080: provided port is not in the valid range. The range of valid ports is 30000-32767
30095
```

Refused, and the Service keeps `30095`. A node port must be in the range set
aside for this use, from 30000 to 32767. It keeps a Service from taking the
port of a program of the node itself, such as SSH (22).

## 📚 Exercise 6: a node port already taken

A node port is open on every node: two Services therefore cannot have the
same one. `kubectl create service nodeport` creates a NodePort Service without
starting from a Deployment. Try to create a second one on `30095`, then on
`30096`:

```bash
kubectl create service nodeport vitrine-bis --tcp=80:8080 --node-port=30095 -n essai-nodeport
kubectl create service nodeport vitrine-bis --tcp=80:8080 --node-port=30096 -n essai-nodeport
kubectl get services -n essai-nodeport
```

```text
error: failed to create NodePort service: Service "vitrine-bis" is invalid: spec.ports[0].nodePort: Invalid value: 30095: provided port is already allocated
service/vitrine-bis created
NAME          TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
vitrine       NodePort   10.101.247.28   <none>        80:30095/TCP   17s
vitrine-bis   NodePort   10.103.51.183   <none>        80:30096/TCP   0s
```

`provided port is already allocated`: `30095` already belongs to the
`vitrine` Service, across the whole cluster, whatever the namespace. `30096`
is free.

## 📚 Exercise 7: close the nodes that run no Pod

By default, a node without a Pod passes the request on to a Pod of another
node, as in exercise 3. This detour hides the client's address. The
`externalTrafficPolicy: Local` setting removes it: each node only serves its
own Pods. The single Pod still runs on `k8s-cp.lab`. Switch the Service to
`Local`, then query both nodes:

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"externalTrafficPolicy":"Local"}}'
sleep 3
curl -s -m 3 http://10.10.50.11:30095/ || echo "pas de réponse (code $?)"
curl -s -m 3 http://10.10.50.12:30095/ || echo "pas de réponse (code $?)"
```

```text
service/vitrine patched
vitrine
pas de réponse (code 28)
```

`k8s-w1.lab`, which runs no `vitrine` Pod, no longer answers: `curl` gives up
after the 3 seconds of `-m 3` (code 28). A user going through that node no
longer reaches the application.

Check it from your workstation, outside the cluster. Open a second terminal on
your machine, the one you run `dsoxlab` from, and run the same two `curl`:

```text
vitrine
pas de réponse (code 28)
```

Same result. Careful: if your Pod runs on `k8s-w1.lab`, it is `k8s-cp.lab`
that will not answer from your workstation. From `k8s-cp.lab` itself, it will
answer anyway, because a node always answers the traffic it sends itself:
always check a `Local` setting from another machine.

Go back to two Pods, one per node:

```bash
kubectl scale deployment vitrine --replicas=2 -n essai-nodeport
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
sleep 10; kubectl get pods -n essai-nodeport -o wide | awk '{print $1, $3, $7}' | column -t
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
NAME                      STATUS   NODE
vitrine-668ff869cd-68fq5  Running  k8s-cp.lab
vitrine-668ff869cd-n6zkt  Running  k8s-w1.lab
```

From your workstation, both nodes answer again:

```text
vitrine
vitrine
```

With `Local`, a node only answers if it runs a Pod of the application.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace,
with its two Services.

```bash
kubectl delete namespace essai-nodeport
```

```text
namespace "essai-nodeport" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-service-nodeport-reparer
dsoxlab check ckad-service-nodeport-reparer
```

```text
╭─ Result: ckad-service-nodeport-reparer ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests        │
╰─────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an application nobody can reach, behind a
badly written NodePort Service. Find what is wrong and repair it.

```bash
dsoxlab run ckad-service-nodeport-reparer
dsoxlab challenge ckad-service-nodeport-reparer
```
