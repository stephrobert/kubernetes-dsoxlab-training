# Route inference requests

The lesson puts an Istio Gateway in front of a group of model servers, an
InferencePool, so that each request goes to the least loaded replica. That is
the challenge of this lab: this course creates no pool, no Gateway and no
route. It works on what the pool relies on: talking to a model server through
its API, recognising its errors, getting a streamed answer, and reading the
metrics the endpoint picker looks at to choose a replica.

You work in the `essai-inference` namespace, with two simulators of a scratch
vLLM server, `sim-libre` and `sim-charge`, which serve a fictitious model,
`essai/petit-modele`, and a `curl` client. The challenge uses other replicas,
in `inference`: you will do it on your own, at the end.

Related page: [Route inference traffic](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/route-llm-inference-traffic/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-router-des-requetes-d-inference
```

You are now connected to `k8s-cp.lab`, the control plane of the kubeadm
cluster. Create the scratch objects. The simulator, `llm-d-inference-sim`,
mimics the API of a vLLM server without a GPU. `sim-charge` gets the
`--fake-metrics` option, which makes it publish an invented load: 2 running
requests, 12 waiting, a cache 60 % full.

```bash
kubectl create namespace essai-inference; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sim-libre
  namespace: essai-inference
spec:
  containers:
    - name: vllm-sim
      image: ghcr.io/llm-d/llm-d-inference-sim:v0.7.1@sha256:74211b5dbf27a867fcefae92067701e0a5fcee827f95156d89718bf3e1bfb845
      args: ["--model", "essai/petit-modele", "--port", "8000"]
      env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
---
apiVersion: v1
kind: Pod
metadata:
  name: sim-charge
  namespace: essai-inference
spec:
  containers:
    - name: vllm-sim
      image: ghcr.io/llm-d/llm-d-inference-sim:v0.7.1@sha256:74211b5dbf27a867fcefae92067701e0a5fcee827f95156d89718bf3e1bfb845
      args: ["--model", "essai/petit-modele", "--port", "8000", "--fake-metrics", '{"running-requests":2,"waiting-requests":12,"kv-cache-usage":0.6}']
      env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: essai-inference
spec:
  containers:
    - name: curl
      image: curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40
      command: ["sleep", "3600"]
YAML
kubectl -n essai-inference wait --for=condition=Ready pod --all --timeout=180s; sleep 5
libre=$(kubectl -n essai-inference get pod sim-libre -o jsonpath='{.status.podIP}')
charge=$(kubectl -n essai-inference get pod sim-charge -o jsonpath='{.status.podIP}')
echo "libre=$libre charge=$charge"
```

```text
namespace/essai-inference created
pod/sim-libre created
pod/sim-charge created
pod/client created
pod/client condition met
pod/sim-charge condition met
pod/sim-libre condition met
libre=10.244.223.14 charge=10.244.38.125
```

The outputs shown in this course were captured on this machine on
23 November 2026 (Kubernetes v1.37.2, llm-d-inference-sim v0.7.1).

## 📚 Exercise 1: ask which models are served

A vLLM server speaks the OpenAI API. The `/v1/models` route lists the models
it serves. It is the first question to ask an unknown server:

```bash
kubectl -n essai-inference exec client -- curl -s "http://$libre:8000/v1/models"
```

```text
{"object":"list","data":[{"id":"essai/petit-modele","object":"model","created":1795390878,"owned_by":"vllm","root":"essai/petit-modele","parent":null}]}
```

The server serves one model, `essai/petit-modele`. This exact name, the `id`
field, is what a completion request must carry.

## 💬 Exercise 2: a completion, and an unknown model

Send a completion request, keeping the answer headers (`-D -`) apart from the
body:

```bash
kubectl -n essai-inference exec client -- curl -s -D - -o /tmp/r.json "http://$libre:8000/v1/completions" -H 'Content-Type: application/json' -d '{"model":"essai/petit-modele","prompt":"Bonjour","max_tokens":5}' | grep -i -E '^HTTP|x-inference'
kubectl -n essai-inference exec client -- cat /tmp/r.json
```

```text
HTTP/1.1 200 OK
X-Inference-Pod: sim-libre
X-Inference-Port: 8000
{"id":"cmpl-e4cc7ef2-811e-53d1-b407-386353a4059e","created":1795390878,"model":"essai/petit-modele","usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2},"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":"stop","text":"I "}]}
```

The body gives the generated text (`choices[0].text`) and the token count
(`usage`), the unit in which the work of a model is measured. The simulator
makes up the text, without any meaning. The headers, though, matter:
`X-Inference-Pod` names the replica that answered. Behind a group of
replicas, it is how you know who served the request. Now ask for a model the
server does not have:

```bash
kubectl -n essai-inference exec client -- curl -s -w '\n%{http_code}\n' "http://$libre:8000/v1/completions" -H 'Content-Type: application/json' -d '{"model":"autre-modele","prompt":"Bonjour","max_tokens":5}'
```

```text
{"error":{"message":"The model `autre-modele` does not exist.","type":"NotFoundError","param":null,"code":404}}
404
```

A **404** code and a JSON error that names the requested model. A typo in the
model name therefore looks like a missing route: read the error body before
looking at the network.

## 🌊 Exercise 3: a streamed answer

A model produces its text token by token. With `"stream": true`, the server
sends each piece as soon as it is ready. `curl`'s `-N` option shows the
pieces as they arrive:

```bash
kubectl -n essai-inference exec client -- curl -s -N "http://$libre:8000/v1/completions" -H 'Content-Type: application/json' -d '{"model":"essai/petit-modele","prompt":"Bonjour","max_tokens":3,"stream":true}'
```

```text
data: {"id":"cmpl-311386e2-0629-50f2-96c5-5f7cb5405335","created":1795390878,"model":"essai/petit-modele","usage":null,"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":null,"text":"Today "}]}

data: {"id":"cmpl-311386e2-0629-50f2-96c5-5f7cb5405335","created":1795390878,"model":"essai/petit-modele","usage":null,"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":null,"text":"is "}]}

data: {"id":"cmpl-311386e2-0629-50f2-96c5-5f7cb5405335","created":1795390878,"model":"essai/petit-modele","usage":null,"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":"length","text":"a "}]}

data: [DONE]
```

The answer comes in three `data:` events, one per token, then
`data: [DONE]`. The last piece carries `finish_reason: "length"`: the model
stopped because it reached `max_tokens`. A streamed request keeps the
connection open until the last piece: it is one of the reasons why an
inference request keeps a replica busy much longer than an ordinary web
request.

## 📈 Exercise 4: what the picker reads to choose

The endpoint picker of an InferencePool does not spread requests at random:
it reads the metrics of each replica. Read the three that describe the load,
on your two simulators:

```bash
for p in libre charge; do ip=$(kubectl -n essai-inference get pod sim-$p -o jsonpath='{.status.podIP}'); echo "--- sim-$p"; kubectl -n essai-inference exec client -- curl -s "http://$ip:8000/metrics" | grep -E '^vllm:(num_requests_(running|waiting)|kv_cache_usage_perc|gpu_cache_usage_perc)'; done
```

```text
--- sim-libre
vllm:kv_cache_usage_perc{model_name="essai/petit-modele"} 0
vllm:num_requests_running{model_name="essai/petit-modele"} 0
vllm:num_requests_waiting{model_name="essai/petit-modele"} 0
--- sim-charge
vllm:kv_cache_usage_perc{model_name="essai/petit-modele"} 0.6000000238418579
vllm:num_requests_running{model_name="essai/petit-modele"} 2
vllm:num_requests_waiting{model_name="essai/petit-modele"} 12
```

`sim-charge` publishes 2 running requests, 12 waiting and a KV cache (the
memory where the model keeps the context of the requests) 60 % full.
`sim-libre` publishes zero everywhere. An ordinary Service would send as many
requests to one as to the other, because it reads none of this. The picker
relies on these values to steer away from `sim-charge`. The
`vllm:gpu_cache_usage_perc` metric of the filter does not show up: this
version of the simulator publishes the name `vllm:kv_cache_usage_perc`.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-inference --wait=true --timeout=120s
```

```text
namespace "essai-inference" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-router-des-requetes-d-inference
dsoxlab check k8s-router-des-requetes-d-inference
```

```text
╭─ Result: k8s-router-des-requetes-d-inference ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests              │
╰───────────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: group the replicas of a model in an
InferencePool, serve it through an Istio Gateway, and prove that the requests
avoid the saturated replica.

```bash
dsoxlab run k8s-router-des-requetes-d-inference
dsoxlab challenge k8s-router-des-requetes-d-inference
```
