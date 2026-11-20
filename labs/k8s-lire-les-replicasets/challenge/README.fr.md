# Challenge : Remonter d'un Pod à son Deployment

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Dans le namespace **`replicasets`** :

- le Deployment **`paiement`** fait tourner trois Pods, et il a été mis à jour
  une fois ; - le Deployment **`rapports`** demande deux Pods, et n'en a aucun.

Le fichier **`~/replicasets/releve.txt`** attend ce que vous lirez dans le
cluster.

## 🎯 Ce que vous devez obtenir

1. Après **`replicaset-actif`** : le nom du ReplicaSet de `paiement` qui porte
   ses Pods aujourd'hui.

2. Après **`replicaset-ancien`** : le nom du ReplicaSet de `paiement` gardé à
   zéro Pod depuis la mise à jour.

3. Après **`cause-failedcreate`** : la raison pour laquelle le ReplicaSet de
   `rapports` ne crée aucun Pod, telle que ses événements la donnent.

4. **`rapports` a ses deux Pods disponibles**, et c'est **le même
   Deployment** qu'au départ : vous l'avez réparé, pas recréé.

## 🧭 Les repères utiles

Un Deployment crée un ReplicaSet par version de ses Pods, et c'est le
ReplicaSet qui crée les Pods. Le nom d'un ReplicaSet est celui de son
Deployment, suivi d'une empreinte. Les colonnes de `kubectl get replicaset`
disent lequel porte les Pods. Le champ `ownerReferences` relie chaque objet à
son propriétaire.

Quand un Deployment n'a aucun Pod, la liste des Pods ne dit rien, puisqu'elle
est vide. Remontez d'un étage : c'est le ReplicaSet qui a essayé de créer les
Pods, et la cause de l'échec est dans **ses** événements, à la fin de
`kubectl describe`. Lisez le message en entier : il nomme l'objet cherché, et
le namespace où il le cherche.

Pour réparer, levez la cause sans supprimer le Deployment : soit vous créez ce
qui manque, soit vous changez la description des Pods pour ne plus le
demander. Le ReplicaSet réessaie tout seul, en attendant un peu plus longtemps
après chaque échec : après une longue pause, cela peut prendre plusieurs
minutes. `kubectl rollout restart` fait créer tout de suite un nouveau
ReplicaSet, sans recréer le Deployment.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre fichier, puis les ReplicaSets de `paiement` et l'état de
`rapports`. Ils vérifient aussi que `rapports` est bien le Deployment du
départ.

```bash
dsoxlab check k8s-lire-les-replicasets
```
