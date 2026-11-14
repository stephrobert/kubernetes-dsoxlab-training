# Prioritize Pods and watch a preemption

Guided lab of the "Advanced scheduling" lesson, module 8 of the Kubernetes
course: two PriorityClasses, a worker filled with low-priority Pods, then an
urgent high-priority Pod that gets one of them preempted.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `multi` (one control plane, two workers); the lab sets up the `ordonnancement` namespace |
| Duration | about 25 minutes |
| Related page | [Advanced scheduling, Put into practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/priority-and-preemption/) |

On kind, every node advertises all the host's CPUs: the setup computes the
filling from the worker's actual allocatable. The `cleanup.yaml` removes the
namespace and the PriorityClasses, which are cluster objects.

```bash
dsoxlab run   k8s-prioriser-et-preempter
dsoxlab check k8s-prioriser-et-preempter
```
