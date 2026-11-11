# Épreuve du niveau 1 : livrer et mettre à jour une application

Épreuve de fin de niveau de la formation Kubernetes : d'après un cahier des
charges qui ne nomme aucun objet Kubernetes, livrer une vitrine dans l'espace
de son équipe, la passer à la version suivante sans coupure, et réparer un
composant en panne après en avoir consigné la cause. Notée sur l'état final :
sept critères à poids égal, seuil 70, cinq critères critiques.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `boutique` (Kubernetes 1.37), espaces `livraison` et `entrepot` |
| Durée | environ 60 minutes |
| Page associée | [Épreuve du niveau 1](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/epreuves/livrer-et-mettre-a-jour/) |

```bash
dsoxlab run    k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab check  k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab submit k8s-epreuve-livrer-et-mettre-a-jour
```
