# Give an application its own identity and the least rights

Challenge of the **RBAC and ServiceAccounts** module of the Kubernetes course,
in the Put into practice section of the "ServiceAccounts" lesson: an
observability tool to give its own identity, the right to read the logs of
another namespace's Pods and nothing more, a token to cut where it serves no
purpose, a default account to strip of the rights it inherited, and a Pod to
harden. Six states, threshold 70, two blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `observatoire` and `production` namespaces |
| Duration | about 40 minutes |
| Related page | [ServiceAccounts, Put into practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-for-developers/) |

```bash
dsoxlab run    k8s-challenge-identite-et-droits-minimaux
dsoxlab check  k8s-challenge-identite-et-droits-minimaux
dsoxlab submit k8s-challenge-identite-et-droits-minimaux
```
