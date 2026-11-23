# Challenge: spot the key signals of a cluster and alert on them with PromQL

## 🧭 The situation

The cluster is monitored by **Prometheus**, which collects the three sources
of the lesson: kube-state-metrics, the kubelet and cAdvisor. It runs in the
`supervision` namespace and answers on `http://localhost:30090` from
`k8s-cp.lab`. It has **no alerting rule** yet.

In the **`signaux`** namespace, two applications are struggling and nobody is
warned:

- `memoire-courte` is killed regularly because it goes over its memory limit;
- `calcul-serre` is constantly slowed down by its CPU limit.

A third one, `temoin-calme`, has limits too, but never reaches them. It must
not trigger any alert.

## 🎯 What you must achieve

1. An alert named **`SignauxOOMKilled`** is **firing** for the
   `memoire-courte` Pod.
2. An alert named **`SignauxThrottling`** is **firing** for the
   `calcul-serre` Pod.
3. Neither of them fires for `temoin-calme`.

## 🔎 Useful pointers

Prometheus reads its rules from the **`prometheus-regles`** ConfigMap of the
`supervision` namespace. Each key of the ConfigMap becomes a file, and
Prometheus loads the files that end with `.yaml`.

A changed ConfigMap takes about a minute to reach the Pod. Prometheus then
only reads its rules again when asked to: `curl -X POST
http://localhost:30090/-/reload`.

`http://localhost:30090/api/v1/rules` shows the loaded rules and their
health, `http://localhost:30090/api/v1/alerts` the pending and firing
alerts. An alert stays pending for the duration of its `for:` before it
fires.

The lesson gives a query for each of the five signals. Test your expressions
on the API before turning them into alerts: `curl -s
http://localhost:30090/api/v1/query --data-urlencode 'query=...'`.

## ✅ How you will know it works

The tests query the Prometheus API: they read the firing alerts, and check
that each one targets the right Pod and not the control Pod. Wait until both
your alerts are firing before running the check.

```bash
dsoxlab check k8s-reperer-les-signaux-d-un-cluster
```
