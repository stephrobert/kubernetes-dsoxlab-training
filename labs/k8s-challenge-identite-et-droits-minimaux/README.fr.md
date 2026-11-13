# Donner à une application sa propre identité et le moindre droit

Challenge du module **RBAC et ServiceAccounts** de la formation Kubernetes, dans
la section Mettre en pratique de la leçon « ServiceAccounts » : un outil
d'observation à doter de sa propre identité, le droit de lire le journal des Pods
d'un autre namespace et rien de plus, un jeton à couper là où il ne sert pas,
un compte par défaut à dépouiller des droits qu'il a hérités, et un Pod à durcir.
Six états, seuil 70, deux bloquants.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose les namespaces `observatoire` et `production` |
| Durée | environ 40 minutes |
| Page associée | [ServiceAccounts, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-developpeurs/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-identite-et-droits-minimaux
dsoxlab check  k8s-challenge-identite-et-droits-minimaux
dsoxlab submit k8s-challenge-identite-et-droits-minimaux
```
