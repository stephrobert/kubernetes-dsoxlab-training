# Challenge : Lire pourquoi quatre Pods restent en Pending et placer chacun

## La situation

Le cluster kubeadm compte trois nœuds : le control plane `k8s-cp.lab` et deux
workers, `k8s-w1.lab` et `k8s-w2.lab`. Ce matin, l'équipe a déployé quatre
applications dans le namespace **`placement`**. Aucune n'a démarré : leurs
Pods restent en **Pending**, et `kubectl get pods` ne dit pas pourquoi.

Ce que l'équipe sait de ses besoins :

- **`calcul`** est un petit service de calcul. Quelqu'un a recopié sa demande
  de CPU depuis une machine de calcul intensif.
- **`cache`** a besoin du **disque NVMe**. Il est monté sur **`k8s-w2.lab`**,
  et sur aucun autre nœud.
- **`batch`** tourne sur **`k8s-w1.lab`**, le nœud que l'équipe batch s'est
  réservé : personne d'autre ne doit pouvoir s'y installer.
- **`archives`** range ses fichiers sur un volume de la classe de stockage
  **`lente`**, que l'équipe a demandée exprès. Le cluster n'a aucun
  provisionneur dynamique : un volume de cette classe se déclare à la main,
  par exemple un `hostPath` sous `/srv/archives`.

Vous êtes sur le control plane, avec `kubectl` configuré, en root.

## Ce que vous devez obtenir

1. Un **ConfigMap `diagnostic`** dans `placement` porte une clé par
   application, `calcul`, `cache`, `batch` et `archives`, et pour chacune la
   cause de son blocage, en un mot : `ressources`, `selecteur`, `taint` ou
   `volume`.
2. **`calcul`** tourne, avec une demande de CPU qu'un nœud peut donner.
3. **`cache`** tourne sur `k8s-w2.lab`, et garde son exigence de disque NVMe.
4. **`batch`** tourne sur `k8s-w1.lab`, et le nœud reste réservé.
5. **`archives`** tourne, son volume `archives-data` est lié dans la classe
   `lente`, et l'application peut y écrire.

## Les repères

La méthode de la leçon, en quatre étapes : repérer les Pods en Pending, lire
l'événement **`FailedScheduling`** de chacun, croiser avec l'état des nœuds
(étiquettes, taints, capacité) et des volumes, puis corriger et vérifier.

Le message d'un `FailedScheduling` dit pourquoi **chaque** nœud a été écarté.
Une partie de ces raisons est du **bruit de fond** : un nœud écarté parce que
le Pod en demande un autre n'est pas la cause du blocage. La cause est la
raison qui écarte les nœuds que ce Pod pourrait réellement utiliser.

Une correction juste ne retire pas la contrainte qui bloque : elle la
satisfait. Supprimer un `nodeSelector` ou une taint ferait démarrer le Pod, au
prix de ce que l'équipe avait demandé.

## Comment vous saurez que ça marche

Les tests lisent le ConfigMap de diagnostic, puis, pour chaque application,
vérifient qu'un Pod est prêt, sur le bon nœud, et que la contrainte d'origine
est toujours là. Pour `archives`, ils écrivent un fichier dans le volume.

```bash
dsoxlab check cka-placer-un-pod-pending
```
