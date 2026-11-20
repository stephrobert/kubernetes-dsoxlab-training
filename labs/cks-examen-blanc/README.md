# CKS mock exam: 16 tasks in 120 minutes

Certification capstone of the Kubernetes course, hosted by the CKS exercises
page. Sixteen tasks in the exam format, spread like the six domains of the
official CKS v1.37 curriculum, graded on the cluster's final state, no hint.
The threshold is the real exam's, 67%.

Twenty requirements at 5 points: dsoxlab grades the share of passed tests, so a 10%
task carries two requirements.

| Domain | Weight | Tasks |
|---|---|---|
| Cluster Setup | 15 | 1, 2, 3 |
| Cluster Hardening | 15 | 4, 5 |
| System Hardening | 10 | 6, 7 |
| Minimize Microservice Vulnerabilities | 20 | 8, 9, 10 |
| Supply Chain Security | 20 | 11, 12, 13 |
| Monitoring, Logging and Runtime Security | 20 | 14, 15, 16 |

The setup installs Traefik, trivy 0.74.0, cosign 3.1.3 and crane 0.22.1, a
local registry, and the starting state of each task: a profiler left open, a
service account bound to cluster-admin, a privileged Pod, an API key in clear
text, an image by tag, an unsigned image, an API server that audits nothing, a
miner hidden in one Pod out of four. The AppArmor profile is dropped on the
worker only. The `cleanup.yaml` restores the control plane manifests and
removes everything, cluster-wide objects and node files included.

Istio, Falco and gVisor are not installed: the control plane node has 4 GB, and
a mock exam must fit the validator's time budget. Pod-to-Pod encryption and
sandboxed runtimes stay in their unit labs (`cks-istio-mtls-lockdown`,
`cks-runtime-sandbox-gvisor`); the miner of task 16 is found without Falco.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; tasks 6 and 16 run on the worker `k8s-w1.lab` |
| Duration | 120 minutes |
| Related page | [CKS exercises](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/certifications/cks/exercises/) |

```bash
dsoxlab run    cks-examen-blanc
dsoxlab check  cks-examen-blanc
dsoxlab submit cks-examen-blanc
```
