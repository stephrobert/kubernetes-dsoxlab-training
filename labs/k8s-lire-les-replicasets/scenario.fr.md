# Remonter d'un Pod à son Deployment

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Dans le namespace **`replicasets`** :

- le Deployment **`api`** fait tourner trois réplicas, et il a été mis à jour
  une fois ;
- le Deployment **`compte-absent`** demande deux réplicas, et n'en a aucun.

Le relevé **`~/replicasets/releve.txt`** attend ce que vous lirez dans le
cluster.

## Ce que vous devez obtenir

1. **`replicaset-actif`** donne le nom du ReplicaSet de `api` qui porte ses
   réplicas aujourd'hui.

2. **`replicaset-ancien`** donne le nom du ReplicaSet de `api` gardé à zéro
   réplica depuis la mise à jour.

3. **`cause-failedcreate`** dit pourquoi le ReplicaSet de `compte-absent` ne
   crée aucun Pod, tel que ses événements le disent.

4. **`compte-absent` a ses deux réplicas disponibles**, et c'est **le même
   Deployment** que celui du départ : il a été réparé, pas recréé.

## Les repères utiles

Un Deployment ne crée pas ses Pods lui-même : il crée un ReplicaSet par version
de son modèle de Pod, et c'est le ReplicaSet qui crée les Pods. Le nom d'un
ReplicaSet est celui de son Deployment suivi d'un hash du modèle, et les
colonnes de `kubectl get replicaset` disent lequel porte les réplicas.
`ownerReferences` relie chaque objet à son propriétaire.

Quand un Deployment n'a aucun Pod, la liste des Pods ne dit rien, puisqu'il n'y
en a pas. Remontez d'un étage : c'est le ReplicaSet qui a tenté de créer les
Pods, et c'est dans **ses** événements, en fin de `kubectl describe`, que
l'échec est écrit.

Pour réparer, levez la cause sans supprimer le Deployment : soit vous créez ce
qui manque, soit vous corrigez le modèle de Pod pour ne plus le demander. Le
contrôleur réessaie seul, avec un délai qui s'allonge à chaque échec : après
une longue pause, il peut attendre plusieurs minutes. `kubectl rollout restart`
fait créer tout de suite un nouveau ReplicaSet, sans recréer le Deployment.

## Comment vous saurez que c'est bon

Les tests lisent le relevé, puis les ReplicaSets de `api` et l'état de
`compte-absent`. L'identité de `compte-absent` est comparée à celle du départ.

```bash
dsoxlab check k8s-lire-les-replicasets
```
