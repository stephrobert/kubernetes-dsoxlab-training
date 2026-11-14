# Enforce an admission rule and prove the refusal, without guidance

Challenge of the **Admission policies** module of the Kubernetes course, in the
Put into practice section of the "VAP vs Kyverno vs Gatekeeper" lesson: the
restricted Pod Security Standard on one namespace, a privileged Pod to rebuild
without any of its flaws on another, and a native admission policy that
refuses images named by a tag on a third, without touching the rest. Ten
states, threshold 70, two blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `vitrine`, `paiement`, `production` and `recette` namespaces |
| Duration | about 45 minutes |
| Related page | [VAP vs Kyverno vs Gatekeeper](https://www.stephane-robert.info/en/docs/devsecops/runtime/vap-vs-kyverno-gatekeeper/) |

```bash
dsoxlab run    k8s-challenge-faire-refuser-par-admission
dsoxlab check  k8s-challenge-faire-refuser-par-admission
dsoxlab submit k8s-challenge-faire-refuser-par-admission
```
