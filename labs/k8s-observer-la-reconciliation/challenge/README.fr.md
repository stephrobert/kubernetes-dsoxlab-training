# Challenge : Observer la réconciliation du control plane

## 📍 La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre kubectl le vise déjà. Dans le namespace **`reconciliation`**,
le Deployment **`vitrine`** fait tourner trois Pods. Le fichier
**`~/reconciliation/releve.txt`** attend vos réponses.

## 🎯 Ce que vous devez obtenir

Deux suppressions, **dans cet ordre**. Après chacune, le cluster doit revenir
à l'état demandé.

1. Vous avez **supprimé un Pod** de `vitrine`, et son ReplicaSet l'a recréé.

2. Vous avez ensuite **supprimé le ReplicaSet** de `vitrine`. Il a été
   remplacé, et `vitrine` est revenu à **trois Pods disponibles**, sans que
   le Deployment ait été modifié.

3. Après **`pod-recree`** : le nom du Pod que le ReplicaSet a créé pour
   remplacer celui que vous avez supprimé.

4. Après **`uid-du-nouveau-replicaset`** : l'UID du ReplicaSet qui a remplacé
   celui que vous avez supprimé.

## 🧭 Les repères utiles

Vous n'avez rien à relancer à la main : les contrôleurs corrigent l'écart
tout seuls. Pour le voir, relancez `kubectl get pods` juste après chaque
suppression, et comparez les noms et les âges.

Chaque contrôleur note ce qu'il fait. Quand un ReplicaSet crée un Pod, il
écrit un événement `SuccessfulCreate` sur lui-même, avec le nom du Pod.
Relevez ce nom avant de supprimer le ReplicaSet : ses Pods partent avec lui.
Deux objets peuvent porter le même nom l'un après l'autre. L'**UID** est
l'identifiant unique que Kubernetes donne à un objet à sa création : il se lit
dans `metadata.uid`.

Supprimez seulement le Pod, puis seulement le ReplicaSet. N'utilisez pas
`kubectl rollout restart` : il crée lui aussi un nouveau ReplicaSet, mais en
modifiant le Deployment.

Sur ce cluster, les événements sont gardés **24 heures** (une heure par défaut
dans Kubernetes). Après une longue pause, ceux du lab ont disparu : relancez
alors `dsoxlab reset k8s-observer-la-reconciliation`.

## ✅ Comment vous saurez que c'est bon

Les tests comparent le cluster à l'état de départ du lab : le ReplicaSet du
départ, ses événements, ses Pods, et le Deployment, qui ne doit pas avoir été
modifié.

```bash
dsoxlab check k8s-observer-la-reconciliation
```
