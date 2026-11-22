# Livrer une application avec Helm et GitOps, depuis une image construite

Challenge du module **Empaqueter et livrer** de la formation Kubernetes : une
image à construire et à pousser dans le registre du cluster, une release Helm
installée depuis un fichier de values et épinglée par digest, une mise à jour
suivie d'un retour en arrière, et un dépôt Git qu'Argo CD doit suivre jusqu'à
la synchronisation. Six exigences, seuil 70, deux bloquantes.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab installe Argo CD, un registre local et un dépôt Git, et pose le travail dans `~/livraison/` |
| Durée | environ 60 minutes |
| Page associée | [GitOps](https://www.stephane-robert.info/docs/devops/delivery/gitops/) |

```bash
dsoxlab run    k8s-challenge-livrer-avec-helm-et-gitops
dsoxlab check  k8s-challenge-livrer-avec-helm-et-gitops
dsoxlab submit k8s-challenge-livrer-avec-helm-et-gitops
```
