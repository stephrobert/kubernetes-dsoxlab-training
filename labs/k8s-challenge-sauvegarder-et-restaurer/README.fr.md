# Challenge : sauvegarder, restaurer et remettre un cluster en ordre

Challenge du module Administrer le cluster du niveau 4, sans procédure : une
sauvegarde fraîche d'etcd, une restauration depuis la sauvegarde de la veille,
un dépôt de manifestes à migrer hors des API retirées, des certificats à
renouveler. Noté sur l'état du cluster ; le nettoyage ramène etcd sur
`/var/lib/etcd`.

| | |
|---|---|
| Cible | `k8s-cp.lab`, cluster kubeadm du catalogue |
| Durée | environ 50 minutes |
| Page associée | [PKI du cluster, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pki-cluster-kubernetes/#mettre-en-pratique) |

```bash
dsoxlab run   k8s-challenge-sauvegarder-et-restaurer
dsoxlab check k8s-challenge-sauvegarder-et-restaurer
```
