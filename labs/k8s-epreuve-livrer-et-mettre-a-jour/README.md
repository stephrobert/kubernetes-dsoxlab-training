# Level 1 test: ship and update an application

End-of-level test of the Kubernetes course: from requirements that name no
Kubernetes object, ship a storefront and move it to the next version without
downtime. Graded on the final state (pass mark 70, four critical requirements).

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37) |
| Duration | about 45 minutes |
| Paired page | [Kubernetes course](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/) (in French; the test page is being written) |

```bash
dsoxlab run   k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab check k8s-epreuve-livrer-et-mettre-a-jour
```
