# Reach an application from the machine

An application running in the cluster cannot be reached directly from your
machine: the addresses of Pods and Services only exist inside the cluster. To
try it anyway, kubectl opens **tunnels**: `kubectl port-forward` links a port
of your machine to a Pod or a Service, and `kubectl proxy` opens access to the
cluster API. The lesson shows these three commands when everything works. This
course makes you read their messages when something is wrong: a Service with
the wrong target port, a local port already taken, a Service without a Pod.

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

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: an application without a Service

Create the scratch namespace and the `miroir` application: two agnhost Pods, a
small test server, listening on port 9090. On the `/hostname` path, each Pod
answers its own name.

```bash
kubectl create namespace essai-acces
kubectl create deployment miroir \
  --image=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6 \
  --replicas=2 -n essai-acces -- /agnhost netexec --http-port=9090
kubectl rollout status deployment/miroir -n essai-acces --timeout=180s | tail -1
kubectl get pods -n essai-acces
```

```text
namespace/essai-acces created
deployment.apps/miroir created
deployment "miroir" successfully rolled out
NAME                      READY   STATUS    RESTARTS   AGE
miroir-78b9b787d7-jbxhr   1/1     Running   0          1s
miroir-78b9b787d7-jht9z   1/1     Running   0          1s
```

## 📚 Exercise 2: a tunnel to a Service with the wrong port

`kubectl expose` picks values without telling you. `--dry-run=client -o yaml`
shows the manifest it would write, without creating anything:

```bash
kubectl expose deployment miroir --port=80 -n essai-acces --dry-run=client -o yaml
```

```text title="Excerpt of the output"
spec:
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: miroir
```

Without `--target-port`, it reuses the value of `--port`: `targetPort: 80`.
But the Pods listen on 9090. Create this faulty Service for real, and look at
what it found:

```bash
kubectl expose deployment miroir --port=80 -n essai-acces
kubectl get endpointslices -n essai-acces -l kubernetes.io/service-name=miroir
```

```text
service/miroir exposed
NAME           ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
miroir-nhpgp   IPv4          80      10.244.0.20,10.244.0.21   0s
```

Both Pods are there: the selector is right. The `PORTS` column says `80`, the
port where the Service will send requests. Open a tunnel to this Service.
`kubectl port-forward` runs as long as the command runs: start it in the
background (the final `&`), with its messages in a log, and give it two
seconds to open. Ports read "local, then remote": `19090:80` links port 19090
of the machine to port 80 of the Service.

```bash
kubectl port-forward service/miroir 19090:80 -n essai-acces > /tmp/tunnel-faux.log 2>&1 &
sleep 2
curl -s -m 3 "http://127.0.0.1:19090/hostname"; echo "code curl : $?"
cat /tmp/tunnel-faux.log
```

```text
code curl : 52
Forwarding from 127.0.0.1:19090 -> 80
Forwarding from [::1]:19090 -> 80
Handling connection for 19090
E1120 11:59:54.701770   14943 portforward.go:549] "An error occurred forwarding" err="error forwarding port 80 to pod 195d9c4f5fccf6ab1cd97c7a7ecf76e2471a519cf3bb60070716019321468575, uid : failed to execute portforward in network namespace \"/var/run/netns/cni-be65d530-395b-d828-cc7d-20007401e83d\": failed to connect to localhost:80 inside namespace \"195d9c4f5fccf6ab1cd97c7a7ecf76e2471a519cf3bb60070716019321468575\", IPv4: dial tcp4 127.0.0.1:80: connect: connection refused IPv6 dial tcp6 [::1]:80: connect: connection refused " localPort=19090 remotePort=80
error: lost connection to pod
```

`curl` exits with code 52: the connection opened, then closed without an
answer. The log says why: `failed to connect to localhost:80 inside namespace
... connection refused`. The tunnel reached the Pod, on port 80, and nothing
listens there. The last line, `lost connection to pod`, says that the tunnel
stopped on its own. Replace the Service with one that has the right target
port:

```bash
kubectl delete service miroir -n essai-acces
kubectl expose deployment miroir --port=80 --target-port=9090 -n essai-acces
kubectl get endpointslices -n essai-acces -l kubernetes.io/service-name=miroir
```

```text
service "miroir" deleted from essai-acces namespace
service/miroir exposed
NAME           ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
miroir-w6svj   IPv4          9090    10.244.0.20,10.244.0.21   0s
```

The `PORTS` column now says `9090`, the port where the Pods listen.

## 📚 Exercise 3: a tunnel to the Service does not spread the load

Open a tunnel to the fixed Service, on local port 19091, then send four
requests. The `echo` adds the line break that the answer lacks:

```bash
kubectl port-forward service/miroir 19091:80 -n essai-acces > /tmp/tunnel-svc.log 2>&1 &
sleep 2
for i in 1 2 3 4; do curl -s "http://127.0.0.1:19091/hostname"; echo; done
cat /tmp/tunnel-svc.log
```

```text
miroir-78b9b787d7-jbxhr
miroir-78b9b787d7-jbxhr
miroir-78b9b787d7-jbxhr
miroir-78b9b787d7-jbxhr
Forwarding from 127.0.0.1:19091 -> 9090
Forwarding from [::1]:19091 -> 9090
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
Handling connection for 19091
```

Four times the same Pod. A tunnel to a Service does **not** spread requests:
at startup, kubectl picks **one** Pod of the Service, and the whole tunnel
leads to it. The log confirms it: `-> 9090`, the port of the Pod, not 80, the
port of the Service. Close this tunnel by killing job number 1:

```bash
kill %1
```

## 📚 Exercise 4: the tunnel dies with its process

Open a tunnel, check that it answers, close it, then query it again:

```bash
kubectl port-forward service/miroir 19092:80 -n essai-acces > /tmp/tunnel-2.log 2>&1 &
sleep 2
curl -s "http://127.0.0.1:19092/hostname"; echo
kill %1
sleep 1
curl -s -m 2 http://127.0.0.1:19092/hostname || echo "plus rien sur 19092 (code $?)"
```

```text
miroir-78b9b787d7-jbxhr
plus rien sur 19092 (code 7)
```

A tunnel is not a cluster object, like a Service: it is a **process** on your
machine. Once the process is killed, the local port leads nowhere (`curl`
exits with code 7, connection refused). If you close your SSH session, your
tunnels stop with it.

## 📚 Exercise 5: a local port already taken

A local port serves only one tunnel at a time. Open one on 19093, then try to
open a second one on the same port, in the foreground this time:

```bash
kubectl port-forward service/miroir 19093:80 -n essai-acces > /tmp/tunnel-a.log 2>&1 &
sleep 2
kubectl port-forward service/miroir 19093:80 -n essai-acces; echo "code du second tunnel : $?"
```

```text
Unable to listen on port 19093: Listeners failed to create with the following errors: [unable to create listener: Error listen tcp4 127.0.0.1:19093: bind: address already in use unable to create listener: Error listen tcp6 [::1]:19093: bind: address already in use]
error: unable to listen on any of the requested ports: [{19093 9090}]
code du second tunnel : 1
```

Refused: `address already in use`. Without the `sleep 2`, the second tunnel
could start before the first one and take the port in its place. If a tunnel
refuses to start, first look for an old tunnel still open on the same port.
Close the first one:

```bash
kill %1
```

## 📚 Exercise 6: go through the API with kubectl proxy

`kubectl proxy` opens local access to the **cluster API**, with your kubectl
rights. Through the API, you also reach a Service, at a long but regular
address:
`/api/v1/namespaces/<namespace>/services/<service>:<port>/proxy/<path>`.
Start the proxy, then query `miroir` twice: with a path, then with nothing
after `proxy`. The `-w` option of `curl` prints the HTTP code and the
redirect address:

```bash
kubectl proxy --port=8001 > /tmp/proxy.log 2>&1 &
sleep 2
cat /tmp/proxy.log
curl -s "http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname"; echo
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy
```

```text
Starting to serve on 127.0.0.1:8001
miroir-78b9b787d7-jbxhr
301 http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/
```

The first request goes through the API, then through the Service, to a Pod.
The second one gets a `301` code: the API redirects to the same address ending
with a slash. A browser follows this redirect by itself, `curl` does not.

Now scale `miroir` down to zero Pods, wait for the Pods to go away, then query
again:

```bash
kubectl scale deployment miroir --replicas=0 -n essai-acces
kubectl wait --for=delete pod -l app=miroir -n essai-acces --timeout=60s
curl -s -w "\ncode HTTP %{http_code}\n" http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname
```

```text title="Excerpt of the output"
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {},
  "status": "Failure",
  "message": "no endpoints available for service \"miroir\"",
  "reason": "ServiceUnavailable",
  "code": 503
}
code HTTP 503
```

Through the API, the failure is spelled out: `no endpoints available`, with
code 503. Bring back two Pods, check that the Service answers again, then
close the proxy:

```bash
kubectl scale deployment miroir --replicas=2 -n essai-acces
kubectl rollout status deployment/miroir -n essai-acces --timeout=120s | tail -1
sleep 2
curl -s "http://127.0.0.1:8001/api/v1/namespaces/essai-acces/services/miroir:80/proxy/hostname"; echo
kill %1
```

```text title="Excerpt of the output"
deployment "miroir" successfully rolled out
miroir-78b9b787d7-dxbt8
```

Unlike `port-forward`, a single proxy gives access to every Service of the
cluster.

## 🧹 Clean up

First delete what you created during the exercises: the scratch namespace,
with everything in it, and the tunnel logs.

```bash
kubectl delete namespace essai-acces
rm -f /tmp/tunnel-*.log /tmp/proxy.log
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
