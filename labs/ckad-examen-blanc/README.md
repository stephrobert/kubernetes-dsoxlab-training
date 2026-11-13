# CKAD mock exam: 17 tasks in 120 minutes

Certification capstone of the Kubernetes course, hosted by the CKAD exercises
page. Seventeen tasks in the exam format, spread like the domains of the
official CKAD v1.37 curriculum, graded on the cluster's final state, no hint.
The threshold is the real exam's, 66%, read in the Linux Foundation's CKA, CKAD
and CKS FAQ.

Twenty states at 5 points: dsoxlab grades the share of passed tests, so a 10%
task carries two states.

| Domain | Weight | Tasks |
|---|---|---|
| Application Design and Build | 20 | 1, 2, 3 |
| Application Deployment | 20 | 4, 5, 6 |
| Application Observability and Maintenance | 15 | 7, 8, 9 |
| Application Environment, Configuration and Security | 25 | 10, 11, 12, 13, 14 |
| Services and Networking | 20 | 15, 16, 17 |

Helm and image building are out of the course in the curriculum map: they are
not in the exam. The setup installs Traefik and local-path, and sets a
kubeconfig, the `k` alias and completion on both task hosts.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster |
| Duration | 120 minutes |
| Related page | [CKAD exercises](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/certifications/ckad/exercices/) |

```bash
dsoxlab run    ckad-examen-blanc
dsoxlab check  ckad-examen-blanc
dsoxlab submit ckad-examen-blanc
```
