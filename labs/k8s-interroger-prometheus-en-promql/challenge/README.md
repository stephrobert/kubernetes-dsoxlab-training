# Challenge: answer operations questions with PromQL

## 🧭 The situation

The cluster is monitored by **Prometheus**, which collects kube-state-metrics,
the kubelet and cAdvisor. It answers on `http://localhost:30090` from
`k8s-cp.lab`.

The operations team is preparing its dashboard and asks you for four PromQL
queries. It wants to find them in the **`requetes`** ConfigMap of the
**`atelier-promql`** namespace, one query per key.

In this namespace, the `relance-auto` Pod exits with an error every ten
seconds, then restarts.

## 🎯 What you must achieve

The `requetes` ConfigMap carries these four keys:

1. **`memoire-par-namespace`**: the memory used by containers
   (`container_memory_working_set_bytes`), added up **per namespace**. One
   series per namespace, with the `namespace` label only. Leave out the
   series without a container.
2. **`top3-cpu-pods`**: the **three** Pods that use the most CPU, measured
   over the **last 5 minutes** (`container_cpu_usage_seconds_total`). One
   series per Pod, with the `namespace` and `pod` labels. Leave out the
   series without a container here too.
3. **`p95-duree-api`**: the **95th percentile** of the duration of the HTTP
   requests Prometheus serves itself
   (`prometheus_http_request_duration_seconds`), over **5 minutes**, **per
   handler**.
4. **`redemarrages-atelier`**: the number of restarts of the containers of
   `atelier-promql` over the **last 10 minutes**, one series per container,
   with the original labels.

## 🔎 Useful pointers

Test each query on the API before storing it in the ConfigMap:

```bash
curl -s http://localhost:30090/api/v1/query --data-urlencode 'query=up' | jq '.data.result'
```

A counter is not read as is: the lesson shows the function that gives a rate
per second, and the one that gives an increase over a duration.

After an aggregation, only the labels you keep remain. A percentile is
computed on the buckets of a histogram, keeping the `le` label.

A ConfigMap is created with `kubectl create configmap ... --from-literal=key=value`,
one option per key. Put each query between single quotes.

## ✅ How you will know it works

For each key, the test evaluates your query and a reference query **at the
same instant**, then compares both results series by series: same labels,
same values. A query that keeps one label too many, or forgets a filter,
returns other series and does not pass.

```bash
dsoxlab check k8s-interroger-prometheus-en-promql
```
