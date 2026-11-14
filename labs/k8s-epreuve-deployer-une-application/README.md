# Level 2 test: deploy an application that keeps its data

End-of-level-2 test of the Kubernetes course: from requirements that name no
object, deploy the shop with its data. A reliable storefront shipped by
Kustomize, a database with a stable identity, a scheduled backup, an agent per
node and a custom resource. Ten criteria, pass mark 70, five critical.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `multi` (one control plane, two workers); the lab sets up the `magasin` namespace and the `Sauvegarde` CRD |
| Duration | about 90 minutes |
| Related page | [Épreuve du niveau 2](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/exam-deploy-an-application/) |

```bash
dsoxlab run    k8s-epreuve-deployer-une-application
dsoxlab check  k8s-epreuve-deployer-une-application
dsoxlab submit k8s-epreuve-deployer-une-application
```
