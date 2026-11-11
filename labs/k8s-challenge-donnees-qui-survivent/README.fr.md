# Garder des données au-delà de la vie d'un Pod

Challenge du module **Stockage persistant** de la formation Kubernetes, dans la
section Mettre en pratique de la leçon « StorageClass » : une revendication
servie par une StorageClass, un fichier témoin qui survit à son Pod, une
reclaim policy, et une revendication Pending à diagnostiquer avant de la
corriger. Six exigences, seuil 70, trois bloquantes.

| | |
|---|---|
| Cible | `k8s-kind.lab`, cluster kind `lab` ; le lab pose le namespace `archives` et une revendication Pending |
| Durée | environ 40 minutes |
| Page associée | [StorageClass, section Mettre en pratique](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/#mettre-en-pratique) |

```bash
dsoxlab run    k8s-challenge-donnees-qui-survivent
dsoxlab check  k8s-challenge-donnees-qui-survivent
dsoxlab submit k8s-challenge-donnees-qui-survivent
```
