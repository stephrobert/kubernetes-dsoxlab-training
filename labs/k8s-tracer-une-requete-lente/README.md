# Trace a slow request

The lesson plugs Istio into an OpenTelemetry collector and Jaeger, deploys a
waypoint, has the trace context forwarded, and finds the slow hop in a trace.
That is the challenge of this lab: this course configures no tracing. It
works on what can be measured without traces and on what traces rely on:
where the time of a request goes, what a client-side timeout does to a slow
request, what the trace context really is, and how to query Jaeger without a
graphical interface.

You work in the `essai-trace` namespace, outside the mesh, with a podinfo
application, `info`, that can answer late on request, and a client `sonde`.
The challenge uses other services, inside the mesh: you will do it on your
own, at the end.

Related page: [Trace a slow request through the Istio mesh](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/trace-slow-request-istio/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-tracer-une-requete-lente
```

You are now connected to `k8s-cp.lab`, the control plane of the kubeadm
cluster. Create the scratch objects: podinfo and its Service, and a `curl`
client:

```bash
kubectl create namespace essai-trace
kubectl -n essai-trace create deployment info --image=ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
kubectl -n essai-trace expose deployment info --port 9898
kubectl -n essai-trace run sonde --image=curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40 --command -- sleep 3600
kubectl -n essai-trace rollout status deployment info --timeout=120s
kubectl -n essai-trace wait --for=condition=Ready pod/sonde --timeout=120s; sleep 5
```

```text
namespace/essai-trace created
deployment.apps/info created
service/info exposed
pod/sonde created
Waiting for deployment "info" rollout to finish: 0 of 1 updated replicas are available...
deployment "info" successfully rolled out
pod/sonde condition met
```

The `sleep 5` matters: in a first attempt, the calls made right away were
refused (`curl` code 7, connection refused): give the application a few
seconds after the deployment. The outputs shown in this course were captured
on this machine on 23 November 2026 (Kubernetes v1.37.2, podinfo 6.17.0,
Jaeger 2.23.0).

## ⏱️ Exercise 1: where the time of a request goes

`curl -w` prints measures taken during the request. Three are enough to know
where the time goes: the connection established (`time_connect`), the first
byte of the answer received (`time_starttransfer`) and the end
(`time_total`). podinfo answers right away on `/`, and one second later on
`/delay/1`:

```bash
for chemin in / /delay/1; do kubectl -n essai-trace exec sonde -- curl -s -o /dev/null -w "$chemin : connexion %{time_connect}s, premier octet %{time_starttransfer}s, total %{time_total}s\n" "http://info:9898$chemin"; done
```

```text
/ : connexion 0.000789s, premier octet 0.001583s, total 0.001603s
/delay/1 : connexion 0.000834s, premier octet 1.002589s, total 1.002773s
```

On `/delay/1`, the connection (`connexion`) takes less than a millisecond, as
on `/`. The second is lost **between the connection and the first byte**
(`premier octet`): the server got the request and took one second to answer.
If the time were lost before the connection, you would look at the network or
DNS. A trace says the same thing hop by hop, when the request goes through
several services.

## ⌛ Exercise 2: a client timeout turns slowness into an error

Call the same slow route with a maximum delay of 0.5 second, as a hurried
client would:

```bash
kubectl -n essai-trace exec sonde -- curl -s -m 0.5 -o /dev/null -w '%{http_code}\n' 'http://info:9898/delay/1'; echo "code=$?"
```

```text
000
command terminated with exit code 28
code=28
```

No HTTP code (`000`) and `curl` code 28, timeout: the client gave up. The
server finished its second of work without knowing it. Seen from the client,
a slow dependency then looks like an outage, and the client log says
"timeout", never "slow". Finding the real cause is why we trace.

## 🧵 Exercise 3: the trace context is just a header

A trace links hops through an HTTP header, `traceparent` (W3C Trace Context
standard). It carries the trace identifier, the identifier of the calling
hop, and a sampling flag. Send one to podinfo, whose `/headers` route returns
the headers it received:

```bash
kubectl -n essai-trace exec sonde -- curl -s -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' 'http://info:9898/headers' | grep -i -A1 traceparent
```

```text
  "Traceparent": [
    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
```

The header arrives as it is. It splits into four fields separated by dashes:
the version (`00`), the trace identifier on 32 characters, the identifier of
the calling hop on 16, and `01`, which asks for recording. Nothing in the
network copies it for you: if an application calls another service without
sending this header on, the next hop starts a new trace.

## 🔎 Exercise 4: query Jaeger without an interface

Jaeger runs in the `observabilite` namespace, without an address exposed
outside the cluster. The API server can relay a request to a Service: this is
how you read the Jaeger API from `kubectl`, without `port-forward`. Ask for
the list of services Jaeger knows:

```bash
kubectl get --raw '/api/v1/namespaces/observabilite/services/http:jaeger:16686/proxy/api/v3/services'
```

```text
{"services":["jaeger"]}
```

Jaeger only knows one service, itself: nothing sends traces yet. The path
reads like this: `services/http:jaeger:16686/proxy` designates the `jaeger`
Service, its port `16686`, over HTTP, and everything after it is passed to
Jaeger (`/api/v3/services`). Once tracing is plugged in, the mesh services
will show up in this list.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-trace --wait=true --timeout=120s
```

```text
namespace "essai-trace" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge, with a new slow service drawn at random. It asks you to
confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-tracer-une-requete-lente
dsoxlab check k8s-tracer-une-requete-lente
```

```text
╭─ Result: k8s-tracer-une-requete-lente ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests       │
╰────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: plug Istio tracing into the collector, get
the spans into Jaeger, and find, in a single trace, which service slows the
requests down.

```bash
dsoxlab run k8s-tracer-une-requete-lente
dsoxlab challenge k8s-tracer-une-requete-lente
```
