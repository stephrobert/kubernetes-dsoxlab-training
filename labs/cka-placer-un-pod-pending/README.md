# Read why four Pods stay Pending and get each one placed

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competency
"Troubleshoot clusters and nodes", and *Workloads and Scheduling* domain,
competency "Configure Pod admission and scheduling".

A Pending Pod has no error to show: the scheduler found no node. The reason is
written once, in the `FailedScheduling` event, among the background noise of
nodes rejected for other reasons. This lab sets the first four causes of the
lesson, one per application, and asks to fix them without removing the
constraint that blocks.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster, with its two workers |
| Duration | about 25 minutes |
| Lesson | [Diagnostiquer un Pod Pending](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/pods-pending-kubernetes/) (French) |

```bash
dsoxlab run   cka-placer-un-pod-pending
dsoxlab check cka-placer-un-pod-pending
```
