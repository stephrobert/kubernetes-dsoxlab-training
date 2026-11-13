# CKA mock exam: 17 tasks in 120 minutes

Certification capstone of the Kubernetes course, hosted by the CKA exercises
page. Seventeen tasks in the exam format, spread like the domains of the
official CKA v1.37 curriculum, graded on the cluster's final state, no hint. The
threshold is the real exam's, 66%, read in the Linux Foundation's CKA, CKAD and
CKS FAQ.

Twenty states at 5 points: dsoxlab grades the share of passed tests, so a 10%
task carries two states.

| Domain | Weight | Tasks |
|---|---|---|
| Storage | 10 | 1, 2 |
| Troubleshooting | 30 | 3, 4, 5, 6 |
| Workloads and Scheduling | 15 | 7, 8, 9 |
| Cluster Architecture, Installation and Configuration | 25 | 10, 11, 12, 13 |
| Servicing and Networking | 20 | 14, 15, 16, 17 |

The setup installs Traefik (Ingress and Gateway API v1.6.2) and local-path,
sets a kubeconfig, the `k` alias and completion on both task hosts, then takes the worker's kubelet
out of service. The `cleanup.yaml` brings the worker back and removes
everything, cluster-wide objects included.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the worker `k8s-w1.lab` is down at the start |
| Duration | 120 minutes |
| Related page | [CKA exercises](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/cka/exercices/) |

```bash
dsoxlab run    cka-examen-blanc
dsoxlab check  cka-examen-blanc
dsoxlab submit cka-examen-blanc
```
