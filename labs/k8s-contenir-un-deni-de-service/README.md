# Contain a denial of service inside its namespace

Guided lab of the "Denial of service: exhausting a cluster" lesson, in the
Threat model and frameworks module of the Kubernetes course (level 5, KCSA
objective "Denial of Service"). A workload with no limits runs in a test
namespace: cap it with a ResourceQuota and a LimitRange, prove the refusal and
the default values with real attempts, bound the running workload, and check
that an application of another namespace keeps answering.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `bac-a-sable` and `annuaire` namespaces |
| Duration | about 30 minutes |
| Related page | [Denial of service: exhausting a cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/deni-de-service-cluster/) (in French) |

The abusive workload is safe for the shared node by construction: each of its
two Pods writes a fixed 96 MiB block into a memory-backed `emptyDir` capped at
128 MiB, then keeps one processor busy in 20-second bursts. Never enough to
put a node under memory pressure.

The `cleanup.yaml` deletes both namespaces, quota and LimitRange included:
nothing is set at cluster scope.

```bash
dsoxlab run   k8s-contenir-un-deni-de-service
dsoxlab check k8s-contenir-un-deni-de-service
```
