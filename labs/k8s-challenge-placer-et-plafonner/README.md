# Place Pods, cap a namespace and scale, without guidance

Challenge of the **Scheduling and capacity** module of the Kubernetes course,
in the Put into practice section of the "Adjusting a Pod's resources" lesson:
a node to reserve for one application, an application to place by required and
preferred node affinity, replicas to spread across nodes, a namespace to cap
and to give default values, and an application to scale on its CPU load. Eight
states, threshold 70, two blocking.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `capacite` (Kubernetes 1.37, one control plane and three workers); the lab sets up the `atelier` namespace |
| Duration | about 50 minutes |
| Related page | [Adjusting a Pod's resources, Put into practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/vertical-pod-scaling/) |

```bash
dsoxlab run    k8s-challenge-placer-et-plafonner
dsoxlab check  k8s-challenge-placer-et-plafonner
dsoxlab submit k8s-challenge-placer-et-plafonner
```
