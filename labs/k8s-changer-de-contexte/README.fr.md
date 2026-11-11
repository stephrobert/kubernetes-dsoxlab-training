# Fusionner un kubeconfig et changer de contexte

Lab guidé du module **Fondamentaux** de la formation Kubernetes : ranger et
protéger un kubeconfig reçu, le fusionner sans écraser le sien, renommer son
contexte, basculer dessus et régler son namespace par défaut.

| | |
|---|---|
| Cible | `k8s-kind.lab`, clusters kind `boutique` (contexte de départ) et `lab` (le cluster « reçu ») |
| Durée | environ 20 minutes |
| Page associée | [Kubeconfig et contextes, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-contexte/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-changer-de-contexte
dsoxlab check k8s-changer-de-contexte
```
