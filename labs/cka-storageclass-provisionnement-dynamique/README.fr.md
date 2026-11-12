# Créer sa StorageClass et obtenir un volume qu'aucun administrateur n'a créé

Lab **CKA**, domaine *Storage* (10 % de l'épreuve), StorageClass et
provisionnement dynamique.

Pendant de [`cka-pv-pvc-storageclass`](../cka-pv-pvc-storageclass/), qui porte
sur le provisionnement **statique**, où un administrateur crée le
PersistentVolume à la main. Celui-ci porte sur le cas dynamique : l'apprenant
**crée sa propre StorageClass**, `garde`, qui reprend le provisionneur déjà
installé avec une autre politique, puis en obtient un volume à la demande.

**Le contrôle décisif n'est pas que la revendication soit liée**, mais que le
volume ait été créé pour elle par le provisionneur, et qu'il porte la politique
de `garde`. Créer un volume à la main lierait aussi la revendication : le test
ne s'y laisse pas prendre. Renommer `local-path` en `garde` non plus : la classe
d'origine doit rester en place.

L'état de départ repose sur une distinction que la documentation mentionne à
peine : `storageClassName: ""`, une chaîne **vide**, **désactive explicitement**
le provisionnement dynamique, là où un champ **absent** laisse jouer la classe
par défaut.

Le provisionneur est `local-path-provisioner` v0.0.37 de Rancher, images
épinglées par digest :

| | `local-path` (installée) | `garde` (à créer) |
|---|---|---|
| provisionneur | `rancher.io/local-path` | le même |
| mode de liaison | `WaitForFirstConsumer` | `WaitForFirstConsumer` |
| politique | `Delete`, le volume suit la revendication | `Retain`, le volume reste |

Le `cleanup.yaml` retire le namespace, les volumes que `Retain` a gardés, la
classe `garde`, le provisionneur et son namespace, et efface
`/opt/local-path-provisioner` sur le nœud.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 30 minutes |
| Leçon jumelée | [StorageClass](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/#mettre-en-pratique) |

```bash
dsoxlab run   cka-storageclass-provisionnement-dynamique
dsoxlab check cka-storageclass-provisionnement-dynamique
```
