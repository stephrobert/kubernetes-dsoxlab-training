# Installer et configurer kubectl

Lab guidé du module **Fondamentaux** de la formation Kubernetes : installer le
binaire officiel de kubectl en version épinglée après avoir vérifié son
empreinte, activer la complétion bash avec l'alias `k`, puis vérifier qu'il
atteint un cluster.

| | |
|---|---|
| Cible | `k8s-kind.lab` ; le lab prépare un cluster kind et votre kubeconfig, puis retire kubectl |
| Durée | environ 20 minutes |
| Page associée | [Installer et configurer kubectl, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-installation-configuration/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-installer-kubectl
dsoxlab check k8s-installer-kubectl
```
