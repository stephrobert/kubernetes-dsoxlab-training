# Plafonner un namespace sans bloquer ceux qui oublient de se déclarer

## La situation

Le namespace **`equipe-produit`** a été ouvert à une équipe, et il n'a **ni plafond ni
valeurs par défaut**.

Deux conséquences, et l'une n'est pas visible tout de suite. L'équipe peut
réclamer tout le cluster, personne ne l'en empêchera. Et ses développeurs
déploient des conteneurs qui ne déclarent aucune ressource, que l'ordonnanceur
place donc à l'aveugle.

Une application, le Deployment **`catalogue`**, tourne déjà dans ce namespace.
Elle demande 50m de CPU et 32Mi de mémoire.

## Ce que vous devez obtenir

1. Un Pod qui demanderait **64 CPU** est **refusé à la création**. Aujourd'hui,
   il est accepté et reste simplement en attente d'une place qui n'existe pas :
   personne ne l'a refusé.

2. Un Pod qui ne déclare **aucune** ressource est **accepté**, et il repart avec
   des `requests` **et** des `limits` qu'il n'avait pas écrites.

3. Le Deployment `catalogue` continue de tourner.

## Les repères utiles

Deux objets sont nécessaires, et ils ne font pas la même chose. L'un plafonne le
**total** consommé par le namespace. L'autre fournit des valeurs par défaut à
chaque conteneur qui n'en déclare pas, **à son arrivée**.

Poser le premier **seul** casse le namespace, et c'est le piège de ce lab : dès
qu'un plafond porte sur les `requests`, tout Pod qui n'en déclare pas devient
invalide, l'API ne pouvant décompter ce qui n'est pas déclaré.

Du côté des valeurs par défaut, **deux champs distincts** sont à remplir : l'un
alimente ce que le conteneur demande, l'autre ce qu'il ne pourra pas dépasser.
Ils ne portent pas le même nom, et il faut les deux.

Un plafond trop bas empêcherait `catalogue` de se replacer au prochain
redémarrage. Ce serait une panne, pas une maîtrise des ressources.

## Comment vous saurez que c'est bon

Les deux tests sont des preuves **actives** : ils créent réellement les deux
Pods, l'un extravagant et l'autre muet, et constatent le refus du premier et la
complétion du second. Relire les objets posés ne prouverait rien : un plafond
qui ne porte pas sur les bonnes ressources est un objet parfaitement valide qui
ne plafonne rien.

```bash
dsoxlab check cka-resourcequota-limitrange
```
