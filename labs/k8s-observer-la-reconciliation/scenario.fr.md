# Observer la réconciliation du control plane

## La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre `kubectl` le vise déjà. Dans le namespace **`reconciliation`**,
le Deployment **`vitrine`** fait tourner trois réplicas. Le relevé
**`~/reconciliation/releve.txt`** attend vos réponses.

## Ce que vous devez obtenir

Deux suppressions, **dans cet ordre**, chacune suivie d'un retour à l'état
demandé :

1. Un Pod de `vitrine` a été **supprimé**, et son ReplicaSet l'a recréé.

2. Puis le **ReplicaSet** de `vitrine` a été supprimé, il a été remplacé, et
   `vitrine` est revenu à **trois réplicas disponibles**, sans que le
   Deployment ait été modifié.

3. **`pod-recree-par`** nomme le contrôleur qui a recréé le Pod.

4. **`replicaset-recree-par`** nomme le contrôleur qui a recréé le ReplicaSet.

## Les repères utiles

Personne ne relance rien à la main : les contrôleurs du control plane
comparent sans cesse l'état demandé à l'état observé, et agissent sur l'écart.
Regardez-le se produire avec `kubectl get pods -w` dans un second terminal
pendant que vous supprimez.

Chaque contrôleur signe ce qu'il fait. Un ReplicaSet qui crée un Pod écrit un
événement `SuccessfulCreate` sur lui-même ; un Deployment qui crée un
ReplicaSet écrit un événement `ScalingReplicaSet` sur lui-même.
`kubectl describe` les montre dans la colonne **From**,
`kubectl get events -o wide` dans la colonne SOURCE : c'est le nom exact à
consigner.

Supprimez seulement le Pod, puis seulement le ReplicaSet. Un
`kubectl rollout restart` créerait lui aussi un nouveau ReplicaSet, mais en
modifiant le Deployment : ce n'est pas ce que vous observez ici.

Les événements sont conservés **24 heures** sur ce cluster (une heure par
défaut dans Kubernetes). Après une pause plus longue, ceux du lab ont disparu :
`dsoxlab reset k8s-observer-la-reconciliation` repose la situation.

## Comment vous saurez que c'est bon

Les tests comparent le cluster à l'état de départ du lab : le ReplicaSet
initial, ses événements, et la génération du Deployment.

```bash
dsoxlab check k8s-observer-la-reconciliation
```
