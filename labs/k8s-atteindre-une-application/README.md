# Reach an application from the machine

An application running in the cluster cannot be reached directly from your
machine: the addresses of Pods and Services only exist inside the cluster. To
try it anyway, kubectl opens **tunnels**: `kubectl port-forward` links a port
of your machine to a Pod or a Service, and `kubectl proxy` opens access to the
cluster API. In this course, you create a Service after first looking at what
it will contain, you open tunnels to a Pod then to a Service, and you go
through the API.

You work in a scratch namespace, `essai-acces`, with a `miroir` application.
The challenge will ask you for the same work on another application: you will
do it on your own, at the end.

Related page: [kubectl expose, port-forward and proxy](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-expose-port-forward-proxy/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-atteindre-une-application
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: an application without a Service

Create the scratch namespace and the `miroir` application: two agnhost Pods, a
small test server, listening on port 8080. On the `/hostname` path, each Pod
answers its own name.

```bash
kubectl create namespace essai-acces
kubectl create deployment miroir --image=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6 --replicas=2 -n essai-acces -- /agnhost netexec --http-port=8080
kubectl rollout status deployment/miroir -n essai-acces --timeout=180s | tail -1
kubectl get pods -n essai-acces
```

```text
namespace/essai-acces created
deployment.apps/miroir created
deployment "miroir" successfully rolled out
NAME                      READY   STATUS    RESTARTS   AGE
miroir-67cbf77d75-8xqv7   1/1     Running   0          1s
miroir-67cbf77d75-dknsx   1/1     Running   0          1s
```

## 📚 Exercise 2: look at a Service before creating it

`kubectl expose` creates a Service for you, and picks several values without
telling you. `--dry-run=client -o yaml` shows the manifest it would write,
**without creating anything**:

```bash
kubectl expose deployment miroir --port=80 -n essai-acces --dry-run=client -o yaml
```

```text
apiVersion: v1
kind: Service
metadata:
  labels:
    app: miroir
  name: miroir
  namespace: essai-acces
spec:
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: miroir
status:
  loadBalancer: {}
```

Two things to read:

- `selector: app: miroir`: it took the Deployment selector;
- `targetPort: 80`: without `--target-port`, it reuses the value of `--port`.
  But the Pods listen on 8080: this Service would have found nothing.

Create the real Service, with the right target port, then check that it found
both Pods:

```bash
kubectl expose deployment miroir --port=80 --target-port=8080 -n essai-acces
kubectl get endpointslices -n essai-acces -l kubernetes.io/service-name=miroir
```

```text
service/miroir exposed
NAME           ADDRESSTYPE   PORTS   ENDPOINTS               AGE
miroir-pg69k   IPv4          8080    10.244.0.8,10.244.0.7   0s
```

## 📚 Exercise 3: a tunnel to a Pod

`kubectl port-forward` links a port of your machine to a port in the cluster.
It runs as long as the command runs: start it in the background (the final
`&`), with its messages in a log. Ports read "local, then remote": `19090:8080`
links port 19090 of the machine to port 8080 of the Pod.

```bash
POD=$(kubectl get pods -n essai-acces -o jsonpath='{.items[0].metadata.name}')
echo $POD
kubectl port-forward pod/$POD 19090:8080 -n essai-acces > /tmp/tunnel-pod.log 2>&1 &
```

```text
miroir-67cbf77d75-8xqv7
```

The shell also prints a `[1]` line followed by a process number: that is the
number of the background job. Now query the local port (the `echo` adds the
line break the answer does not have), then read the tunnel log:

```bash
curl -s 'http://127.0.0.1:19090/hostname'; echo
cat /tmp/tunnel-pod.log
```

```text
miroir-67cbf77d75-8xqv7
Forwarding from 127.0.0.1:19090 -> 8080
Forwarding from [::1]:19090 -> 8080
Handling connection for 19090
```

The Pod answers through the tunnel. The log says where the tunnel leads, then
one `Handling connection` line per request. Close it by killing job number 1:

```bash
kill %1
```

The shell confirms with a `Terminated` line.

## 📚 Exercise 4: a tunnel to the Service

A tunnel can also target the Service. Open it on local port 19091, then send
four requests:

```bash
kubectl port-forward service/miroir 19091:80 -n essai-acces > /tmp/tunnel-svc.log 2>&1 &
for i in 1 2 3 4; do curl -s 'http://127.0.0.1:19091/hostname'; echo; done
cat /tmp/tunnel-svc.log
```

```text
miroir-67cbf77d75-8xqv7
miroir-67cbf77d75-8xqv7
miroir-67cbf77d75-8xqv7
miroir-67cbf77d75-8xqv7
Forwarding from 127.0.0.1:19091 -> 8080
Forwarding from [::1]:19091 -> 8080
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
```

Four times the same Pod. A tunnel to a Service does **not** spread the
requests: at start-up, kubectl picks **one** Pod of the Service, and the whole
tunnel leads to it. The log confirms it: `-> 8080`, the Pod port, not 80, the
Service port. Close this tunnel:

```bash
kill %1
```

## 📚 Exercise 5: the tunnel dies with its process

Open a tunnel, check that it answers, close it, then query it again:

```bash
kubectl port-forward service/miroir 19092:80 -n essai-acces > /tmp/tunnel-2.log 2>&1 &
curl -s 'http://127.0.0.1:19092/hostname'; echo
kill %1
curl -s -m 2 http://127.0.0.1:19092/hostname || echo "plus rien sur 19092 (code $?)"
```

```text
miroir-67cbf77d75-8xqv7
plus rien sur 19092 (code 7)
```

A tunnel is not an object of the cluster, like a Service: it is a **process**
on your machine. Once the process is killed, the local port leads nowhere
(`curl` exits with code 7, connection refused; "plus rien sur" means "nothing
left on"). If you close your SSH session, your tunnels stop with it.

## 📚 Exercise 6: a local port already taken

A local port serves only one tunnel at a time. Open one on 19093, then try to
open a second one on the same port, in the foreground this time:

```bash
kubectl port-forward service/miroir 19093:80 -n essai-acces > /tmp/tunnel-a.log 2>&1 &
kubectl port-forward service/miroir 19093:80 -n essai-acces; echo "code du second tunnel : $?"
```

```text
Unable to listen on port 19093: Listeners failed to create with the following errors: [unable to create listener: Error listen tcp4 127.0.0.1:19093: bind: address already in use unable to create listener: Error listen tcp6 [::1]:19093: bind: address already in use]
error: unable to listen on any of the requested ports: [{19093 8080}]
code du second tunnel : 1
```

Refused: `address already in use`. If a tunnel refuses to start, first look for
an old tunnel still open on the same port. Close the first one:

```bash
kill %1
```

## 📚 Exercise 7: go through the API with kubectl proxy

`kubectl proxy` opens local access to the **cluster API**, with your kubectl
rights. Through the API, you can also reach a Service, at a long but regular
address: `/api/v1/namespaces/<namespace>/services/<service>:<port>/proxy/<path>`.

```bash
kubectl proxy --port=8001 > /tmp/proxy.log 2>&1 &
cat /tmp/proxy.log
curl -s 'http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname'; echo
kill %1
```

```text
Starting to serve on 127.0.0.1:8001
miroir-67cbf77d75-8xqv7
```

The request went through the API, then through the Service, to a Pod. Unlike
`port-forward`, a single proxy gives access to every Service of the cluster.

## 🧹 Clean up

Delete the scratch namespace, with everything in it:

```bash
kubectl delete namespace essai-acces
```

```text
namespace "essai-acces" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-atteindre-une-application
dsoxlab check k8s-atteindre-une-application
```

```text
╭─ Result: k8s-atteindre-une-application ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests        │
╰─────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: expose an application through a Service,
then open a tunnel to it and write down the Pod that answers you.

```bash
dsoxlab run k8s-atteindre-une-application
dsoxlab challenge k8s-atteindre-une-application
```
