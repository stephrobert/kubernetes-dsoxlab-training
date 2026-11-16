# Rendre lisible la santé d'un cluster et rédiger son bulletin

Lab **CKA**, domaine *Troubleshooting*, compétence « Monitor cluster and
application resource usage ».

Sans metrics-server, `kubectl top` est muet, et l'on confond facilement ce
qu'un nœud consomme avec ce qu'il a réservé. Ce lab fait installer
metrics-server sur un cluster kubeadm, puis lire les deux mesures pour rédiger
un bulletin de santé.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 25 minutes |
| Leçon jumelée | [Observer la santé d'un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/observer-sante-cluster-kubernetes/) |

```bash
dsoxlab run   k8s-observer-la-sante-d-un-cluster
dsoxlab check k8s-observer-la-sante-d-un-cluster
```
