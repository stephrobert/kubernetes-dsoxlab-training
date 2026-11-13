# Appliquer une recommandation du VPA

## La situation

Dans le namespace **`dimensionnement`**, le Deployment **`catalogue`** tourne en
deux réplicas avec des requests choisies au hasard : **5m** de CPU et **16Mi**
de mémoire, sous une limite CPU de **50m**. L'équipe veut des requests fondées
sur la consommation réelle, sans laisser un automate redémarrer ses Pods.

Le cluster kubeadm porte déjà **metrics-server** et le **Vertical Pod
Autoscaler** 1.8.1. Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. Un VerticalPodAutoscaler **`catalogue`**, dans `dimensionnement`, qui vise le
   Deployment `catalogue` en mode **`Off`** : il recommande, il n'agit pas.
2. Ce VPA a produit une **recommandation** pour le conteneur `catalogue`.
3. Les **requests** du Deployment conviennent : le **CPU** entre la **borne
   basse** (`lowerBound`) et la **borne haute** (`upperBound`) de cette
   recommandation ; la **mémoire** au moins égale à la **consommation que mesure
   metrics-server**, et au plus égale à la borne haute.
4. Les Pods en marche portent ces requests.
5. Le VPA n'a **évincé aucun Pod**.

## Les repères utiles

Le recommender lit les mesures toutes les minutes : la première recommandation
arrive quelques minutes après la création du VPA. `kubectl describe vpa` la
montre, conteneur par conteneur.

La cible (`target`) n'est pas une valeur à recopier les yeux fermés. Le
recommender ne descend jamais sous un **plancher de 250Mi** de mémoire par Pod,
même pour un conteneur qui en consomme moins : sa borne basse mémoire n'est que
ce plancher. `kubectl top pods` dit ce que le conteneur consomme vraiment, et
c'est sur cette mesure, avec une marge, que se règle la mémoire.

Une **limite CPU trop basse** bride la consommation mesurée, donc la cible CPU :
relever une request au-dessus de la limite est refusé par l'API. Choisissez un
CPU entre les deux bornes, cohérent avec la limite.

Un VPA dans un autre mode que `Off` évince les Pods pour leur donner ses
valeurs : c'est exactement ce que l'équipe refuse ici.

## Comment vous saurez que c'est bon

Les tests lisent le VPA et sa recommandation au moment du check, puis comparent
les requests du Deployment et des Pods en marche à ses bornes et à la
consommation que mesure metrics-server. Ils cherchent enfin
la trace d'une éviction par le VPA dans le namespace.

```bash
dsoxlab check k8s-appliquer-une-recommandation-vpa
```
