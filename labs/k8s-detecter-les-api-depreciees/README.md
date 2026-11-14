# Detect and migrate removed APIs

Guided lab of the "Managing API deprecations" lesson, Administer the cluster
module of level 4: six legacy manifests, four of them in a removed API
(PodDisruptionBudget, HorizontalPodAutoscaler, CronJob, Ingress), to find,
migrate without changing what they describe, and apply.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `migration` namespace |
| Duration | about 30 minutes |
| Related page | [API deprecations, Put into practice section](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/api-deprecations/#mettre-en-pratique) (in French) |

```bash
dsoxlab run   k8s-detecter-les-api-depreciees
dsoxlab check k8s-detecter-les-api-depreciees
```
