# Fix a cluster's CIS findings, without guidance

Challenge of the **Harden the cluster** module of the Kubernetes course, in the
Put into practice section of the "Audit Logs" lesson: an API server to harden
without breaking it, a CIS finding to fix on three control plane components
and to prove with a second kube-bench audit, and a two-level audit policy
whose trace must appear in the log. Seven states, threshold 70, two blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `conformite` namespace and restores the three control plane manifests at each run |
| Duration | about 50 minutes |
| Related page | [Audit Logs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) |

```bash
dsoxlab run    k8s-challenge-durcir-le-plan-de-controle
dsoxlab check  k8s-challenge-durcir-le-plan-de-controle
dsoxlab submit k8s-challenge-durcir-le-plan-de-controle
```
