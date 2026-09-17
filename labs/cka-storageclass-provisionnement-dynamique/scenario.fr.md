# Obtenir un volume sans qu'un administrateur l'ait créé, et voir ce qu'il devient

## La situation

Dans le namespace **`archives`**, la revendication **`donnees`** réclame 128Mi et
reste **en attente**. Personne ne lui a préparé de volume, et personne ne le
fera : l'équipe qui s'en chargeait à la main n'existe plus.

Le cluster, lui, sait désormais en fabriquer à la demande. Encore faut-il le lui
demander.

## Ce que vous devez obtenir

1. La revendication `donnees` est **liée**, et le volume auquel elle est liée a
   été **créé pour elle** : personne ne l'a préparé d'avance.

2. Un Pod nommé **`registre`** monte cette revendication sur `/data` et y écrit
   un fichier **`/data/temoin`**.

3. La revendication garde son nom et son namespace.

## Les repères utiles

Commencez par regarder ce que le cluster propose, et ce que la revendication
demande. L'écart est là.

Le champ en cause vaut actuellement une **chaîne vide**, ce qui n'est pas la
même chose qu'un champ absent : la chaîne vide **désactive explicitement** le
provisionnement à la demande, tandis qu'un champ absent laisse jouer la classe
par défaut du cluster.

Ce champ **ne se modifie pas** sur une revendication existante.

Ne vous étonnez pas qu'elle reste en attente juste après votre correction : la
classe de ce cluster ne provisionne **qu'au moment où un Pod utilise** la
revendication. `kubectl get storageclass` le montre dans sa colonne
`VOLUMEBINDINGMODE`.

Regardez enfin ce que vous avez obtenu **sans l'avoir demandé** : un volume,
avec une politique que la classe lui impose, et qui décide de son sort le jour
où la revendication disparaîtra.

## Comment vous saurez que c'est bon

Le dernier test ne se contente pas de voir la revendication liée : il vérifie
que le volume appartient bien à la classe, et qu'il en porte la politique.
Créer un volume à la main lierait aussi la revendication, sans rien avoir
provisionné à la demande. C'est le lab voisin, pas celui-ci.

```bash
dsoxlab check cka-storageclass-provisionnement-dynamique
```
