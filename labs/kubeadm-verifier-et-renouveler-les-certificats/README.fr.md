# Vérifier et renouveler les certificats d'un cluster kubeadm

Premier lab guidé de la leçon « PKI d'un cluster Kubernetes », module Administrer
le cluster du niveau 4 : lire les échéances, renouveler les certificats du plan de
contrôle, faire recharger les composants, recopier admin.conf. Le renouvellement
se juge sur les numéros de série, relevés au lancement.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue |
| Durée | environ 30 minutes |
| Page associée | [PKI du cluster, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/#mettre-en-pratique) |

```bash
dsoxlab run   kubeadm-verifier-et-renouveler-les-certificats
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```
