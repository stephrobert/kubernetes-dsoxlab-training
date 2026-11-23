# Query Prometheus with PromQL

The lesson presents PromQL: label selectors, counters read with `rate()` and
`increase()`, aggregation by label, percentiles computed with
`histogram_quantile()` and ranking with `topk()`. This course has you write
each of these queries against the lab's Prometheus, and look at what it
returns.

The course questions use other metrics than the challenge: you will do it on
your own, at the end.

Related page: [PromQL](https://www.stephane-robert.info/en/docs/outils/observabilite/metriques/prometheus/promql/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-interroger-prometheus-en-promql
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm
cluster. The lab installed Prometheus in the `supervision` namespace: from
this node, it answers on `http://localhost:30090`. It collects
kube-state-metrics, the kubelet and cAdvisor on the three nodes.

To query Prometheus without a browser, define a small `q` function. It sends
a PromQL query to the API and prints each series on one line, with its
labels and value (a few technical labels are hidden to keep lines short):

```bash
q() { curl -fsS http://localhost:30090/api/v1/query --data-urlencode "query=$1" | jq -r '.data.result[] | "\(.metric | del(.__name__, .instance, .uid, .id, .name, .image) | to_entries | map("\(.key)=\(.value)") | join(",")) => \(.value[1])"'; }
```

Keep the same terminal until the end: the function only exists in it. The
outputs shown in this course were captured on this machine on 23 November
2026, with Kubernetes v1.37.2 and Prometheus v3.16.0. Values change from one
minute to the next: look at their shape and how they relate, not at the
exact numbers.

## 🔎 Exercise 1: filter by labels

A metric name alone returns all its series. `up` is 1 for each target
Prometheus could read. Then filter it by its `job` label, with a regular
expression, then with an inequality:

```bash
q 'up'
echo '--- job=~"kube"'; q 'up{job=~"kube"}'
echo '--- job=~"kube.*"'; q 'up{job=~"kube.*"}'
echo '--- job!="cadvisor"'; q 'count(up{job!="cadvisor"})'
```

```text
job=cadvisor,node=k8s-cp.lab => 1
job=cadvisor,node=k8s-w2.lab => 1
job=cadvisor,node=k8s-w1.lab => 1
job=kubelet,node=k8s-w1.lab => 1
job=kubelet,node=k8s-w2.lab => 1
job=kubelet,node=k8s-cp.lab => 1
job=prometheus => 1
job=kube-state-metrics => 1
--- job=~"kube"
--- job=~"kube.*"
job=kubelet,node=k8s-w1.lab => 1
job=kubelet,node=k8s-w2.lab => 1
job=kubelet,node=k8s-cp.lab => 1
job=kube-state-metrics => 1
--- job!="cadvisor"
 => 5
```

Eight targets: Prometheus itself, kube-state-metrics, and the kubelet and
cAdvisor on each of the three nodes. `job=~"kube"` returns **nothing**:
PromQL regular expressions are anchored, they must cover the whole value.
You need `kube.*` to find `kubelet` and `kube-state-metrics`. `count()`
counts the series left after the filter.

## 📈 Exercise 2: read a counter with rate() and increase()

`prometheus_http_requests_total` counts the requests Prometheus has served
since it started. Send it 60 requests, one per second, then read the raw
counter, its rate per second over 5 minutes, and its increase over the same
duration:

```bash
for i in $(seq 60); do curl -s -o /dev/null http://localhost:30090/api/v1/query --data-urlencode 'query=up'; sleep 1; done
sleep 30
q 'prometheus_http_requests_total{handler="/api/v1/query"}'
q 'rate(prometheus_http_requests_total{handler="/api/v1/query"}[5m])'
q 'increase(prometheus_http_requests_total{handler="/api/v1/query"}[5m])'
q 'rate(prometheus_http_requests_total{handler="/api/v1/query"}[5m]) * 300'
```

```text
code=200,handler=/api/v1/query,job=prometheus => 127
code=200,handler=/api/v1/query,job=prometheus => 0.2245614035087719
code=200,handler=/api/v1/query,job=prometheus => 67.36842105263158
code=200,handler=/api/v1/query,job=prometheus => 67.36842105263158
```

The raw counter only goes up: it says nothing about the pace. `rate()` gives
a number of requests per second, averaged over 5 minutes. `increase()` gives
a number of requests over those 5 minutes, and it is `rate()` multiplied by
300 seconds, here to the last digit: both functions read the same points. Neither
result is a whole number, because Prometheus extrapolates between its
measurements, taken every 15 seconds.

## ➕ Exercise 3: aggregate by label

`container_memory_working_set_bytes` gives the memory of each container. Add
it up for the whole cluster, then per node. Then count the Pods of each node
with `kube_pod_info`, which publishes one series per Pod:

```bash
q 'sum(container_memory_working_set_bytes{container!=""})'
q 'sum by (node) (container_memory_working_set_bytes{container!=""})'
q 'count by (node) (kube_pod_info)'
```

```text
 => 2518261760
node=k8s-cp.lab => 1849020416
node=k8s-w2.lab => 183332864
node=k8s-w1.lab => 485908480
node=k8s-w1.lab => 20
node=k8s-w2.lab => 16
node=k8s-cp.lab => 24
```

Without `by`, `sum()` removes every label and returns a single number. With
`by (node)`, it keeps the `node` label and returns one value per node. The
`container!=""` filter leaves out the series cAdvisor publishes for the
whole Pod: without it, each container would be counted twice.

## 📊 Exercise 4: a percentile with histogram_quantile()

`prometheus_http_response_size_bytes` is a histogram: the size of each
response falls into buckets bounded by the `le` label. Look at the buckets
of one handler, compute the 95th percentile of response size per handler,
then do the computation again forgetting the `le` label:

```bash
q 'prometheus_http_response_size_bytes_bucket{handler="/api/v1/query"}'
q 'histogram_quantile(0.95, sum by (handler, le) (rate(prometheus_http_response_size_bytes_bucket[5m]))) > 0'
q 'histogram_quantile(0.95, sum by (handler) (rate(prometheus_http_response_size_bytes_bucket[5m])))' | wc -l
```

```text
handler=/api/v1/query,job=prometheus,le=100.0 => 1
handler=/api/v1/query,job=prometheus,le=1000.0 => 6
handler=/api/v1/query,job=prometheus,le=10000.0 => 127
handler=/api/v1/query,job=prometheus,le=100000.0 => 127
handler=/api/v1/query,job=prometheus,le=1e+06 => 127
handler=/api/v1/query,job=prometheus,le=1e+07 => 127
handler=/api/v1/query,job=prometheus,le=1e+08 => 127
handler=/api/v1/query,job=prometheus,le=1e+09 => 127
handler=/api/v1/query,job=prometheus,le=+Inf => 127
handler=/-/ready => 95
handler=/api/v1/targets => 95500
handler=/metrics => 95499.99999999999
handler=/api/v1/query => 9527.868852459016
0
```

Each bucket counts the responses smaller than or equal to its bound: the
numbers only grow up to `+Inf`, which counts them all. `histogram_quantile()`
returns, per handler, the size under which 95 % of the responses fall. The
`> 0` leaves out the handlers that served no response over the window.
Without `le` in the `by`, the function has no buckets left to read and
returns no series: the last command counts 0.

## 🏆 Exercise 5: rank with topk() and filter with a comparison

Rank the three Pods that use the most memory, then keep those over 100 MB.
Finally, add `bool` to the comparison, on the `kube-system` Pods only:

```bash
q 'topk(3, sum by (namespace, pod) (container_memory_working_set_bytes{container!=""}))'
q 'sum by (namespace, pod) (container_memory_working_set_bytes{container!=""}) > 100e6'
q 'sum by (namespace, pod) (container_memory_working_set_bytes{container!="",namespace="kube-system"}) > bool 100e6'
```

```text
namespace=kube-system,pod=kube-apiserver-k8s-cp.lab => 998899712
namespace=tigera-operator,pod=tigera-operator-d78bcd95d-cvjvv => 117825536
namespace=kube-system,pod=kube-controller-manager-k8s-cp.lab => 107343872
namespace=kube-system,pod=kube-apiserver-k8s-cp.lab => 998899712
namespace=kube-system,pod=kube-controller-manager-k8s-cp.lab => 107343872
namespace=supervision,pod=prometheus-db77b7f4b-tsgq8 => 103297024
namespace=tigera-operator,pod=tigera-operator-d78bcd95d-cvjvv => 117825536
namespace=kube-system,pod=etcd-k8s-cp.lab => 0
namespace=kube-system,pod=kube-apiserver-k8s-cp.lab => 1
namespace=kube-system,pod=kube-controller-manager-k8s-cp.lab => 1
namespace=kube-system,pod=kube-proxy-m2nm7 => 0
namespace=kube-system,pod=kube-scheduler-k8s-cp.lab => 0
namespace=kube-system,pod=kube-proxy-75bqj => 0
namespace=kube-system,pod=kube-state-metrics-54cc45d487-c6rtj => 0
namespace=kube-system,pod=coredns-559f6c778d-gnlpc => 0
namespace=kube-system,pod=coredns-559f6c778d-ls5cx => 0
namespace=kube-system,pod=kube-proxy-pcbrz => 0
```

`topk(3, ...)` keeps the three largest values. A comparison alone
**filters**: it keeps only the series that satisfy it, with their original
value. That is why an alert fires as soon as its result is not empty. With
`bool`, the comparison keeps every series and replaces it with 1 or 0.

## 🧹 Clean-up

This course created no object in the cluster: queries write nothing. Leave
the machine and reset the lab. `dsoxlab reset` replays the clean-up and then
the lab preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-interroger-prometheus-en-promql
dsoxlab check k8s-interroger-prometheus-en-promql
```

```text
╭─ Result: k8s-interroger-prometheus-en-promql ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests              │
╰───────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: write the four queries the operations team
asks for, and store them in a ConfigMap.

```bash
dsoxlab run k8s-interroger-prometheus-en-promql
dsoxlab challenge k8s-interroger-prometheus-en-promql
```
