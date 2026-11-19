# Open an application outside the cluster with a NodePort Service

A `ClusterIP` Service can only be reached from inside the cluster. For a user,
outside, to reach the application, the **NodePort** type also opens a port on
**every node** of the cluster. A request sent to that port, on any node, reaches
one of the Pods. In this course, you create a NodePort Service, you reach it
through each node, you choose its port, then you repair a NodePort Service that
leads nowhere.

You work in a scratch namespace, `essai-nodeport`, with a `vitrine`
application. The challenge will ask you to repair another NodePort Service: you
will do it on your own, at the end.

Related page: [Kubernetes Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-service-nodeport-reparer
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: the application, and the node addresses

Create the scratch namespace:

```bash
kubectl create namespace essai-nodeport
```

```text
namespace/essai-nodeport created
```

The `vitrine` application runs in two Pods, which serve the text `vitrine` on
port 8080. The `terminationGracePeriodSeconds: 5` field shortens the stop of a
Pod: the small `httpd` server ignores the stop signal, and Kubernetes would
otherwise wait 30 seconds before cutting it.

```bash
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
          command: ["sh", "-c", "echo vitrine > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - containerPort: 8080
YAML
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
```

```text
deployment.apps/vitrine created
deployment "vitrine" successfully rolled out
```

A NodePort is reached through the address of a node. These addresses show in
the `INTERNAL-IP` column of `kubectl get nodes -o wide`. The `awk` command keeps
only three columns, so that the output fits on screen:

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
```

```text
service/vitrine exposed
NAME      TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.104.107.240   <none>        80:32338/TCP   0s
```

The `PORT(S)` column says `80:32338`. A NodePort Service indeed has **three**
ports, which the detail shows:

```bash
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0]}{"\n"}'
```

```text
{"nodePort":32338,"port":80,"protocol":"TCP","targetPort":8080}
```

- `port` (80): the port of the Service inside the cluster;
- `targetPort` (8080): the container port, where the requests arrive;
- `nodePort` (32338): the port opened on **every node**. You did not choose it:
  Kubernetes picked it at random in its range, from 30000 to 32767.

## 📚 Exercise 3: reach the application through each node

Query the node port on both nodes. The `NP` variable takes the `nodePort`, since
it was picked at random. The `sleep 3` gives the cluster time to open that port
on the nodes:

```bash
sleep 3; NP=$(kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}'); curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

Both nodes answer. Now scale the application down to a single Pod, then look at
which node it runs on:

```bash
kubectl scale deployment vitrine --replicas=1 -n essai-nodeport && kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
sleep 8; kubectl get pods -n essai-nodeport -o wide | awk '{print $1, $3, $7}' | column -t
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
NAME                      STATUS   NODE
vitrine-549565bb45-fgxbm  Running  k8s-cp.lab
```

The only Pod runs on `k8s-cp.lab`. Query both nodes again:

```bash
NP=$(kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}'); curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

`k8s-w1.lab` answers too, although it has no `vitrine` Pod. The port is open on
**all** nodes, and each one passes the request on to the Pod, wherever it runs.
Scale back to two Pods:

```bash
kubectl scale deployment vitrine --replicas=2 -n essai-nodeport && kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
```

## 📚 Exercise 4: choose the node port

A random port does not suit users: they need a fixed address. Set the
`nodePort` to `30095` with `kubectl patch`. The port is identified by its `port`
(80), so that Kubernetes knows which one to change:

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":30095}]}}'
kubectl get service vitrine -n essai-nodeport
```

```text
service/vitrine patched
NAME      TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.104.107.240   <none>        80:30095/TCP   12s
```

`80:30095`: the node port is now the one you chose.

```bash
sleep 3; curl -s http://10.10.50.11:30095/
```

```text
vitrine
```

## 📚 Exercise 5: a port outside the range

Try a node port that is easier to remember, `8080`:

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":8080}]}}'
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}{"\n"}'
```

```text
The Service "vitrine" is invalid: spec.ports[0].nodePort: Invalid value: 8080: provided port is not in the valid range. The range of valid ports is 30000-32767
30095
```

Refused, and the Service keeps `30095`. A node port must be in the range
reserved for that use, from 30000 to 32767. It prevents a Service from taking
the port of a program of the node itself, such as SSH (22).

## 📚 Exercise 6: repair a Service that leads nowhere

`kubectl create service nodeport` creates a NodePort Service without starting
from a Deployment. Create one, `vitrine-cassee`, on node port `30096`, with a
wrong target port, `9090`:

```bash
kubectl create service nodeport vitrine-cassee --tcp=80:9090 --node-port=30096 -n essai-nodeport
kubectl get service vitrine-cassee -n essai-nodeport -o jsonpath='{.spec.selector}{"\n"}'
```

```text
service/vitrine-cassee created
{"app":"vitrine-cassee"}
```

With no Deployment to copy, the command took a selector from the Service name:
`app=vitrine-cassee`. No Pod carries that label. Look at the endpoints, then try
the node port:

```bash
kubectl get endpointslices -n essai-nodeport -l kubernetes.io/service-name=vitrine-cassee
sleep 3; curl -s -m 3 http://10.10.50.11:30096/ || echo "pas de réponse (code $?)"
```

```text
NAME                   ADDRESSTYPE   PORTS     ENDPOINTS   AGE
vitrine-cassee-w6v8m   IPv4          <unset>   <unset>     1s
pas de réponse (code 7)
```

No endpoint, and `curl` exits with code 7: the connection is refused ("pas de
réponse" means "no answer"). First defect, the selector. Fix it so that it
targets the `vitrine` Pods:

```bash
kubectl set selector service vitrine-cassee app=vitrine -n essai-nodeport
sleep 3; kubectl get endpointslices -n essai-nodeport -l kubernetes.io/service-name=vitrine-cassee
curl -s -m 3 http://10.10.50.11:30096/ || echo "pas de réponse (code $?)"
```

```text
service/vitrine-cassee selector updated
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
vitrine-cassee-w6v8m   IPv4          9090    10.244.38.112,10.244.163.40   7s
pas de réponse (code 7)
```

Both Pods are now endpoints, but on port `9090`, where nothing listens. Still no
answer. Second defect, the target port. Fix it:

```bash
kubectl patch service vitrine-cassee -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"targetPort":8080}]}}'
sleep 3; curl -s -m 3 http://10.10.50.11:30096/ || echo "pas de réponse (code $?)"
```

```text
service/vitrine-cassee patched
vitrine
```

The application answers. To repair a Service, go in this order: first the
endpoints (the selector), then the target port, then the node port.

## 🧹 Clean up

Delete the scratch namespace, with everything in it:

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
