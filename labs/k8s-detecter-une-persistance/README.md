# Find and remove what an attacker left behind

Guided lab of the "Persistence: what an attacker leaves behind" lesson, in the
Threat model and frameworks module of the Kubernetes course (level 5, KCSA
objective "Persistence"). A scheduled workload recreates an attacker's access
every minute: find it by listing what is scheduled, who holds which rights and
what the events show, record it, remove it without touching the legitimate
application, and prove the access does not come back.

| | |
|---|---|
| Target | `k8s-cp.lab`, the catalogue's kubeadm cluster; the lab sets up the `facturation` namespace and three cluster-wide objects of the attacker |
| Duration | about 30 minutes |
| Related page | [Kubernetes course](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/), until the lesson is published |

The method is in `scenario.md`: list the scheduled objects, the rights and the
webhooks, read the events and, where the API server writes one, the audit log.

The `cleanup.yaml` deletes the attacker's CronJob first, so that no run in
progress recreates the access, then the namespace, then the
ClusterRoleBindings and the ClusterRole the attacker left, and the record file
on the node.

```bash
dsoxlab run   k8s-detecter-une-persistance
dsoxlab check k8s-detecter-une-persistance
```
