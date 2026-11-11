# Obtenir un volume sans qu'un administrateur l'ait créé, et voir ce qu'il devient

## La situation

Dans le namespace **`archives`**, la revendication **`donnees`** réclame 128Mi et
reste **en attente**. Personne ne lui a préparé de volume, et personne ne le
fera : l'équipe qui s'en chargeait à la main n'existe plus.

Le cluster, lui, sait désormais en fabriquer à la demande. Encore faut-il le lui
demander.

## Ce que vous devez obtenir

1. La revendication `donnees`, qui garde son nom et son namespace, désigne la
   classe **`local-path`**.

2. Elle est **liée**, et le volume auquel elle est liée a été **créé pour elle**
   par le provisionneur de la classe : personne ne l'a préparé d'avance.

3. Ce volume porte la **reclaim policy** que sa classe lui impose.

4. Un Pod nommé **`registre`** monte cette revendication sur **`/data`**.

5. Il y écrit un fichier **`/data/temoin`**, dans le volume.

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

Chaque test vérifie un des cinq états ci-dessus. Le deuxième ne se contente pas
de voir la revendication liée : il vérifie que le provisionneur de la classe a
créé le volume pour cette revendication. Créer un volume à la main, même avec
la bonne classe, lierait aussi la revendication, sans rien avoir provisionné à
la demande. C'est le lab voisin, pas celui-ci.

```bash
dsoxlab check cka-storageclass-provisionnement-dynamique
```
