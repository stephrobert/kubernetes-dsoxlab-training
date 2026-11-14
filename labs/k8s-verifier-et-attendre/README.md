# Preview with diff, wait with wait

Guided lab of the **Deploy your applications** module of the Kubernetes course:
preview with `kubectl diff`, wait with `kubectl wait` and `kubectl rollout
status`, and write a deployment script that stops at the right moment.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab sets up the `paiements` namespace and the `~/deploiement/` folder |
| Duration | about 25 minutes |
| Related page | [kubectl diff and wait, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-wait-diff/) |

```bash
dsoxlab run   k8s-verifier-et-attendre
dsoxlab check k8s-verifier-et-attendre
```
