# Level 3 test: expose, configure and ship an application

End-of-level test of the Kubernetes course: from requirements that name no
Kubernetes object, ship and repair a festival application. Route two web
applications by host and path, repair an inherited component after recording
its cause, isolate the database, place the workloads on a reserved node and
across nodes, cap the namespace, scale the application on a metric, give it
its own identity and harden its container. Graded on the final state: eleven
criteria of equal weight, pass mark 70, six critical criteria, no hint.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `capacite` (Kubernetes 1.37, one control plane and three workers), spaces `festival`, `paiement` and `partenaires` |
| Duration | about 120 minutes |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/) (the test's own page is yet to be published) |

```bash
dsoxlab run    k8s-epreuve-livrer-une-application
dsoxlab check  k8s-epreuve-livrer-une-application
dsoxlab submit k8s-epreuve-livrer-une-application
```
