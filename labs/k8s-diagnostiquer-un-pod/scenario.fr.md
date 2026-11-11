# Diagnostiquer deux Pods en échec

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Dans le namespace **`pods-en-panne`**, deux Pods nus refusent de
travailler :

- **`image-fausse`** n'a jamais démarré ;
- **`plante`** démarre, puis s'arrête, encore et encore.

Le relevé **`~/pods-en-panne/releve.txt`** attend ce que vous lirez dans le
cluster.

## Ce que vous devez obtenir

1. **`raison-image-fausse`** donne la raison pour laquelle le conteneur de
   `image-fausse` attend.

2. **`code-sortie-plante`** donne le code de sortie du conteneur de `plante`
   lors de son dernier arrêt.

3. **`image-fausse` tourne**, sur l'image **`nginx:1.30.5`**, et c'est **le
   même Pod** que celui du départ : son image a été corrigée en place.

4. **`plante` tourne sans redémarrer**, toujours sous le nom `plante` et sur la
   même image `busybox:1.38.0` : seule sa commande a changé, pour une commande
   qui dure (une attente d'une heure, par exemple).

## Les repères utiles

Commencez toujours par la vue d'ensemble, puis descendez vers le détail :
`kubectl get pods -n pods-en-panne` donne les colonnes STATUS et RESTARTS,
`kubectl describe pod` donne l'état du conteneur et, en fin de sortie, les
**Events** qui disent la cause. Un conteneur qui a planté garde la trace de son
dernier arrêt dans le statut du Pod, champ par champ.

Les deux réparations ne se font pas de la même façon, et c'est le cœur du lab.
Un Pod est presque figé une fois créé : **son image** est l'un des rares champs
qui se modifient sur un Pod existant. **Sa commande**, non : pour la changer,
on récupère son manifeste, on le corrige, puis on recrée le Pod sous le même
nom. Recréer `image-fausse` ou garder `plante` sous un autre nom ne répondent
pas à la demande.

## Comment vous saurez que c'est bon

Les tests lisent le relevé, puis l'état des deux Pods dans le cluster.
L'identité de `image-fausse` est comparée à celle du départ.

```bash
dsoxlab check k8s-diagnostiquer-un-pod
```
