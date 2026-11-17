# Fermer l'API server et le kubelet aux clients anonymes sans casser kubeadm join

Lab **CKS**, domaine *Cluster Hardening* (15 % de l'épreuve), compétence
« Restrict access to the Kubernetes API ».

Fermer l'accès anonyme semble tenir en un drapeau, `--anonymous-auth=false`.
Sur un cluster kubeadm, ce drapeau casse la découverte de `kubeadm join`. Ce
lab vous fait garder l'anonyme sur les seuls chemins utiles, fermer le kubelet
et remettre NodeRestriction, sans perdre la possibilité d'ajouter un nœud.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm |
| Durée | environ 35 minutes |
| Leçon jumelée | [Restreindre l'accès à l'API server](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/restreindre-acces-api-server/) |

```bash
dsoxlab run   cks-restreindre-l-acces-anonyme
dsoxlab check cks-restreindre-l-acces-anonyme
```
