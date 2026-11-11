# Un Pod à deux conteneurs et ses budgets de ressources

Lab de la leçon **Requests et Limits** du module « Déployer ses applications »
de la formation Kubernetes, et compétence **CKAD** du domaine *Application
Design and Build* : deux conteneurs, leurs `resources`, et la limite de mémoire
lue dans le cgroup du conteneur, là où le noyau l'applique.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 15 minutes |
| Page associée | [Requests et Limits, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/#mettre-en-pratique) |

```bash
dsoxlab run   ckad-pod-resources-labels
dsoxlab check ckad-pod-resources-labels
```
