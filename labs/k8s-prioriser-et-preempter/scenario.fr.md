# Prioriser des Pods et observer une préemption

## La situation

Sur le cluster kind **`multi`**, le worker **`multi-worker`** est plein : le
Deployment **`remplissage`**, dans le namespace **`ordonnancement`**, y fait
tourner quatre Pods qui se partagent tout son CPU disponible. Aucun n'a de
priorité.

Un traitement urgent doit pourtant passer sur ce nœud. Son manifeste vous
attend dans **`~/lab/urgent.yaml`** : il demande exactement la place d'un Pod
de remplissage, et elle n'existe pas.

## Ce que vous devez obtenir

1. Deux PriorityClass : **`basse`**, de valeur **1000**, et **`haute`**, de
   valeur **100000**. Aucune n'est la classe par défaut du cluster.
2. Les Pods de **`remplissage`** tournent sous la classe **`basse`**.
3. Le Pod **`urgent`** tourne sur **`multi-worker`**, sous la classe
   **`haute`**.
4. Pour lui faire de la place, l'ordonnanceur a **préempté** un Pod de
   remplissage.

Faites-les dans cet ordre : les classes, puis le remplissage, puis le Pod urgent.

## Les repères utiles

Une PriorityClass est un objet du cluster, sans namespace. Un Pod la nomme par
`priorityClassName`, et l'admission traduit ce nom en une `priority` numérique,
**à la création du Pod** : un Pod déjà en marche ne change pas de priorité.

Quand un Pod ne trouve aucune place, l'ordonnanceur cherche des Pods moins
prioritaires dont l'éviction suffirait. Il les évince, et le dit par un
événement **`Preempted`** sur chaque victime. `kubectl get events -n
ordonnancement` le montre.

## Comment vous saurez que c'est bon

Les tests lisent les deux classes, la priorité des Pods de remplissage et du Pod
urgent, le nœud où il tourne, et l'événement de préemption.

```bash
dsoxlab check k8s-prioriser-et-preempter
```
