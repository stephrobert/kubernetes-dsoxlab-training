# Route inference requests by replica load with the Gateway API Inference Extension

## The situation

The kubeadm cluster has **three nodes**, and Istio 1.32 runs on it in ambient
mode, with the **Gateway API Inference Extension** enabled: its CRDs are
installed and Istio's control plane knows how to send traffic to an
`InferencePool`.

In the namespace **`inference`**, a model server answers the OpenAI API
(`/v1/completions`) on port **8000**. It is a vLLM simulator, without GPU,
serving the model `meta-llama/Llama-3.1-8B-Instruct`, in **three replicas**
spread over two Deployments: `modele-libre` (two replicas) and
`modele-sature` (one replica). The last one is **saturated**: its metrics show
a queue of 40 requests and a KV cache 97 % full. Each response carries the
header **`x-inference-pod`**, the name of the Pod that served it.

An **endpoint picker** is already running: the Deployment and the Service
**`selecteur`** (port 9002). It reads the metrics of the replicas and tells
the Gateway which one should take each request. It is **not ready**: it waits
for an `InferencePool` named **`pool-modele`** in `inference`.

The cluster has no load balancer. You are on the control plane, with
`kubectl` configured, as root.

## What you must achieve

1. An **InferencePool** (`inference.networking.k8s.io/v1`) of `inference`
   groups the **three replicas** of the model on port 8000 and names the
   endpoint picker `selecteur`, which becomes ready.
2. A **Gateway** of class `istio` in `inference` has an HTTP listener, and the
   cluster declares it **Programmed**.
3. An **HTTPRoute** attached to the Gateway has the **InferencePool as
   backend**, and it is Accepted with its references resolved.
4. Completion requests sent to the Gateway are **answered by the replicas**.
5. The requests **avoid the saturated replica**: out of 30 requests, it
   receives at most 10 %.

## The method, step by step

**Group the replicas in a pool.** An `InferencePool` is the inference
counterpart of a Service: `spec.selector.matchLabels` picks the Pods,
`spec.targetPorts` gives their port, and `spec.endpointPickerRef` names the
Service of the picker (`name`, `port.number`). The selector must take **all
three** replicas, the saturated one included: the picker can only avoid a
replica it sees. Read the labels with `kubectl get pods -n inference
--show-labels`. Once the pool exists, `kubectl get deploy selecteur -n
inference` turns ready: its logs (`kubectl logs deploy/selecteur`) say what it
found.

**Declare the Gateway.** `gatewayClassName: istio` and an HTTP listener on
port 80. As the cluster has no load balancer, add the annotation
`networking.istio.io/service-type: ClusterIP`, otherwise the Gateway stays
not Programmed.

**Route to the pool, not to a Service.** In the `HTTPRoute`, the `backendRef`
carries `group: inference.networking.k8s.io`, `kind: InferencePool` and the
name of the pool. The Gateway then asks the picker for each request. A
`backendRef` to an ordinary Service would spread requests blindly: a third of
them would land on the saturated replica.

**Measure the spread.** Take the ClusterIP of the Service Istio created for
the Gateway (`kubectl get svc -n inference -l
gateway.networking.k8s.io/gateway-name=<name>`), then send requests and read
the header:

```bash
curl -s -o /dev/null -D - -H 'Content-Type: application/json' \
  -d '{"model":"meta-llama/Llama-3.1-8B-Instruct","prompt":"Question 1","max_tokens":8}' \
  http://<ip>/v1/completions | grep -i x-inference-pod
```

Change the prompt on each request: the picker also favours the replica that
already saw the same prompt.

## How you will know it works

The tests read the pool and check that its selector takes exactly the three
replicas, that the picker is ready, that the Gateway is Programmed and that
the route to the pool is accepted. Then they send real completion requests
through the Gateway and count, header by header, which replica answered.

```bash
dsoxlab check k8s-router-des-requetes-d-inference
```
