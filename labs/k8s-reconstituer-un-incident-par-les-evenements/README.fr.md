# Reconstituer un incident à partir des Events d'un namespace

Lab **CKA**, domaine *Troubleshooting*, compétences « Troubleshoot clusters
and nodes » et « Troubleshoot components ».

Les Events sont le journal d'alerte immédiat du cluster. Ce lab fait lire ceux
d'un namespace où quatre applications sont tombées, chacune d'une façon
différente, pour nommer chaque panne et retrouver laquelle a commencé.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 20 minutes |
| Leçon jumelée | [Analyser les événements Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/analyser-evenements-kubernetes/) |

```bash
dsoxlab run   k8s-reconstituer-un-incident-par-les-evenements
dsoxlab check k8s-reconstituer-un-incident-par-les-evenements
```
