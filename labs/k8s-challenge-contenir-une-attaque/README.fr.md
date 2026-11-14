# Détecter et contenir une persistance et un déni de service

Challenge du module **Modèle de menaces et cadres** de la formation Kubernetes
(niveau 5, KCSA), dans la section Mettre en pratique de la leçon « Déni de
service » : l'accès d'un attaquant que quelque chose recrée sans cesse, à
consigner et à retirer pour de bon sans abîmer l'application légitime, puis une
charge abusive à contenir dans son namespace pendant qu'une autre application
continue de répondre. Sept états, seuil 70, deux bloquants.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue ; le lab pose les namespaces `reservations` et `calcul-lots` et trois objets de l'attaquant à l'échelle du cluster |
| Durée | environ 45 minutes |
| Page associée | [Déni de service : épuiser un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/deni-de-service-cluster/) |

La persistance diffère de celle du lab guidé `k8s-detecter-une-persistance`,
les noms aussi : jouez d'abord les deux labs guidés du module.

La charge abusive est sûre pour le nœud partagé, par construction : un bloc
fixe de 64 Mio par Pod dans un `emptyDir` en mémoire, et un processeur occupé
la moitié du temps.

```bash
dsoxlab run    k8s-challenge-contenir-une-attaque
dsoxlab check  k8s-challenge-contenir-une-attaque
dsoxlab submit k8s-challenge-contenir-une-attaque
```
