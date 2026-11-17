# Trace a slow request through the Istio mesh

## The situation

The kubeadm cluster has **three nodes**: the control plane and two workers.
Istio 1.32 runs on it in **ambient mode**, with **no trace provider**. The
installation file of the mesh is on the control plane:
`/root/istio-ambient.yaml`.

In the namespace **`observabilite`**, outside the mesh, an **OpenTelemetry
collector** (contrib 0.165.0) listens for OTLP on the Service `otel-collector`
(port 4317 for gRPC) and exports everything to **Jaeger** 2.23.0 (Service
`jaeger`, query API and UI on port 16686).

In the namespace **`boutique`**, inside the mesh but **without a waypoint**,
the Pod `client` calls the Service `web`, and `web` calls **both** `api` and
`stock`. Every request takes more than a second, and the team does not know
why: **one** of the two services, `api` or `stock`, is slow. Which one changes
every time the lab starts.

You are on the control plane, with `kubectl`, `istioctl` and `jq`, as root.

## What you must achieve

1. The mesh configuration declares an **opentelemetry provider** that aims at
   `otel-collector.observabilite.svc.cluster.local`, port **4317**.
2. A mesh-wide **Telemetry** in `istio-system` traces **100 %** of requests
   with that provider.
3. A **waypoint** serves the namespace `boutique`, and its Pod is **Ready**.
4. The spans of the waypoint **reach Jaeger**.
5. A **single trace** links a span of `web` to the waypoint span of the hop to
   the slow service.
6. The ConfigMap **`diagnostic`** of `boutique` names the slow service, key
   **`service-lent`**, value `api` or `stock`.

## The method, step by step

**Declare the provider.** A provider lives in `meshConfig`, and only
`istioctl install` rewrites it. Copy `/root/istio-ambient.yaml` to a new file,
add `spec.meshConfig.extensionProviders` with an entry of type `opentelemetry`
(service and port of the collector), then `istioctl install -y -f` that file.
`kubectl -n istio-system get configmap istio -o yaml` shows the result.

**Trace every request.** A `Telemetry` in `istio-system`, without selector,
applies to the whole mesh. Under `tracing`, name the provider and set
`randomSamplingPercentage: 100`: the default samples 1 % of requests.

**Add a waypoint.** ztunnel works at L4: it sees connections, not HTTP
requests, and writes no span. `istioctl waypoint apply -n boutique
--enroll-namespace --wait` creates a waypoint and labels the namespace.
istioctl says « is ready! » before the Pod is: wait for the Pod itself with
`kubectl wait`.

**Look in Jaeger.** Send a few requests from the client (`kubectl -n boutique
exec client -- curl -s -X POST -d bonjour http://web.boutique:9898/echo`),
then open the query API: `kubectl -n observabilite port-forward svc/jaeger
16686:16686 &` and `curl -s localhost:16686/api/v3/services`. If Jaeger knows
nothing but itself, the spans are lost on the way. The waypoint says why only
in its debug log: `istioctl proxy-config log deploy/waypoint -n boutique
--level tracing:debug,grpc:debug`, then `kubectl -n boutique logs
deploy/waypoint`. Look at how the collector's port is declared: Istio picks
the protocol from the port name prefix or from `appProtocol`.

**Get one trace, not one per hop.** The waypoint writes one span per hop, but
the hops end up in the same trace only if `web` forwards the trace context
(the `traceparent` header) on its own calls. podinfo does it only with
`--otel-service-name`. Add it to the command of `web`.

**Read the trace.** `curl -s
"localhost:16686/api/v3/traces?query.serviceName=web&query.startTimeMin=<RFC3339>&query.startTimeMax=<RFC3339>&query.searchDepth=20"`
returns the traces as OTLP JSON. A `jq` filter that prints, for each span,
the service name, the span name and `endTimeUnixNano - startTimeUnixNano` in
milliseconds shows which child of `web` lasts more than a second. The UI on
the same port-forward shows the same thing.

**Write the diagnostic.** `kubectl -n boutique create configmap diagnostic
--from-literal=service-lent=<service>`. Do not repair the slow service: the
check reads its delay to compare.

## How you will know it works

The tests read `meshConfig`, the Telemetry objects, the waypoint and its Pod.
Then they send their own requests and read the Jaeger API: the waypoint's
spans must arrive, and one trace must hold both a span of `web` and the hop
to the slow service. Last, they compare your diagnostic with the service that
carries the delay.

```bash
dsoxlab check k8s-tracer-une-requete-lente
```
