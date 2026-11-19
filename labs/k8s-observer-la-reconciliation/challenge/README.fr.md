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

3. Après **`pod-recree-par`** : le nom du contrôleur qui a recréé le Pod.

4. Après **`replicaset-recree-par`** : le nom du contrôleur qui a recréé le
   ReplicaSet.

## 🧭 Les repères utiles

Vous n'avez rien à relancer à la main : les contrôleurs corrigent l'écart
tout seuls. Pour le voir se produire, lancez `kubectl get pods -w` dans un
second terminal pendant que vous supprimez.

Chaque contrôleur signe ce qu'il fait. Quand un ReplicaSet crée un Pod, il
écrit un événement `SuccessfulCreate` sur lui-même. Quand un Deployment crée
un ReplicaSet, il écrit un événement `ScalingReplicaSet` sur lui-même. Le nom
à recopier est dans la colonne `From` de `kubectl describe`, ou dans la
colonne `SOURCE` de `kubectl get events -o wide`.

Supprimez seulement le Pod, puis seulement le ReplicaSet. N'utilisez pas
`kubectl rollout restart` : il crée lui aussi un nouveau ReplicaSet, mais en
modifiant le Deployment.

Sur ce cluster, les événements sont gardés **24 heures** (une heure par défaut
dans Kubernetes). Après une longue pause, ceux du lab ont disparu : relancez
alors `dsoxlab reset k8s-observer-la-reconciliation`.

## ✅ Comment vous saurez que c'est bon

Les tests comparent le cluster à l'état de départ du lab : le ReplicaSet du
départ, ses événements, et le Deployment, qui ne doit pas avoir été modifié.

```bash
dsoxlab check k8s-observer-la-reconciliation
```
