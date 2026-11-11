# Level 1 test: ship and update an application

End-of-level test of the Kubernetes course: from requirements that name no
Kubernetes object, ship a storefront in the space of its team, move it to the
next version without downtime, and repair a failing component after recording
its cause. Graded on the final state: seven criteria of equal weight, pass mark
70, five critical criteria.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `boutique` (Kubernetes 1.37), spaces `livraison` and `entrepot` |
| Duration | about 60 minutes |
| Related page | [Épreuve du niveau 1](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/epreuves/livrer-et-mettre-a-jour/) |

```bash
dsoxlab run    k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab check  k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab submit k8s-epreuve-livrer-et-mettre-a-jour
```
