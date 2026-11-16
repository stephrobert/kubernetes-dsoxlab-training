# Label a node, show its role and reserve it for one team

**CKA** lab, *Troubleshooting* domain (30 % of the exam), competency
"Troubleshoot clusters and nodes", and *Workloads and Scheduling* domain,
competency "Configure Pod admission and scheduling".

Label, role, annotation, taint: four gestures on a node, and one decision that
matters, the effect of the taint. Picking the wrong effect on a production node
leaves in place what you wanted gone, or the reverse.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster, with its two workers |
| Duration | about 20 minutes |
| Lesson | [Gérer les nœuds](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/gerer-noeuds-kubernetes/) (French) |

```bash
dsoxlab run   cka-etiqueter-et-isoler-un-noeud
dsoxlab check cka-etiqueter-et-isoler-un-noeud
```
