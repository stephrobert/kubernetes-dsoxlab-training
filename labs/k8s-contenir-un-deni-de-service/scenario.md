# Contain a denial of service inside its namespace

## The situation

On the shared kubeadm cluster, the **`bac-a-sable`** namespace is open to
every team for tests. Nothing caps it. The **`gourmand`** Deployment runs
there, two replicas that declare **no requests and no limits**: each one holds
a block of memory and keeps a processor busy in bursts. Here the load is
bounded on purpose, so the node stays safe. A real one would not stop there.

In the **`annuaire`** namespace, an application of two replicas answers behind
its Service. It must keep answering, whatever runs in `bac-a-sable`.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. **`bac-a-sable`** carries a **ResourceQuota** that caps, at most:
   `requests.cpu` **1**, `requests.memory` **1Gi**, `limits.cpu` **2** and
   `limits.memory` **2Gi**.
2. A container that declares no resources in `bac-a-sable` receives **by
   default** requests of **100m** CPU and **128Mi** memory, and limits of
   **300m** CPU and **256Mi** memory.
3. A **creation beyond the quota** is refused by the cluster.
4. The **running Pods** of `gourmand`, still two of them, carry **requests and
   limits**.
5. While `gourmand` runs bounded, the application of **`annuaire`** keeps its
   two replicas and **answers**.

## The method, step by step

**Look at the threat first.** `kubectl get pods -n bac-a-sable -o
custom-columns=NAME:.metadata.name,QOS:.status.qosClass` shows `BestEffort`
Pods: no request, no limit, nothing reserved and nothing capped. `kubectl
describe node` lists, per node, what Pods asked for: these two count for
nothing, whatever they use. A denial of service aims at the processor and
memory of the nodes, the number of Pods and objects, the requests sent to the
API server and the storage.

**Cap the namespace.** A ResourceQuota names each resource it caps:
`requests.cpu`, `requests.memory`, `limits.cpu`, `limits.memory`, and
optionally `pods` or an object count. A key it does not name is not capped.

**Give default values at the same time.** As soon as a quota covers requests
or limits, a Pod that declares none is refused, because the API cannot count
it. A LimitRange of type `Container` fills `defaultRequest` and `default` on
arrival. Set both together, otherwise the next restart of an application of
the namespace fails.

**Test the refusal for real.** Create a Pod asking more than what remains in
the quota: the cluster answers `exceeded quota`, with what is requested, used
and limited. `kubectl describe resourcequota -n bac-a-sable` shows the
counters.

**Bound what already runs.** Quota and default values apply when a Pod is
created, never to Pods already running. `kubectl rollout restart` recreates
those of `gourmand`, which then receive the default values. Do not delete the
workload: the lesson is to contain it while it runs.

**Check the neighbour.** `kubectl get svc -n annuaire` gives the Service
address; a few `curl` requests from the node prove it answers.

## How you will know it works

The tests read the quota of `bac-a-sable`, create two probe Pods there, one
declaring nothing and one asking too much, and look at what the cluster does
with them. Then they read the running Pods of `gourmand` and send real HTTP
requests to `annuaire` while the workload runs.

```bash
dsoxlab check k8s-contenir-un-deni-de-service
```
