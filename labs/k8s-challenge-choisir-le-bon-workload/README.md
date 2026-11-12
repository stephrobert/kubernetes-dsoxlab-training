# Choose and deploy the right workload for three needs

Challenge of the **Advanced workloads** module of the Kubernetes course, in the
Mettre en pratique section of the "Operators and CRDs for developers" lesson:
three needs described without naming any object, a database with a stable
identity, an agent per node and a bounded custom resource. Seven requirements,
pass mark 70, three blocking.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `multi` (one control plane, two workers); the lab sets up the `entrepot` namespace and the CRD to install |
| Duration | about 50 minutes |
| Related page | [Operators et CRDs pour développeurs, Mettre en pratique section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators-crds-developpeurs/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-choisir-le-bon-workload
dsoxlab check  k8s-challenge-choisir-le-bon-workload
dsoxlab submit k8s-challenge-choisir-le-bon-workload
```
