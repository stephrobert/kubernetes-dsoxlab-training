# Explore the API with api-resources and explain

Guided lab of the **Deploy your applications** module of the Kubernetes course:
find the apiVersion and the kind of an unknown CRD, write an object with the
fields only `explain` reveals, add a probe found field by field, and draw up the
full inventory of a namespace.

| | |
|---|---|
| Target | `k8s-kind.lab`, kind cluster `lab`; the lab installs a CRD and the `archives` namespace |
| Duration | about 25 minutes |
| Related page | [kubectl api-resources and explain, Mettre en pratique section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-api-resources-explain/) |

```bash
dsoxlab run   k8s-explorer-l-api
dsoxlab check k8s-explorer-l-api
```
