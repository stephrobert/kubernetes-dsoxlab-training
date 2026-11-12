# Créer sa StorageClass et obtenir un volume qu'aucun administrateur n'a créé

## La situation

Dans le namespace **`archives`**, la revendication **`donnees`** réclame 128Mi et
reste **en attente**. Personne ne lui a préparé de volume, et personne ne le
fera : l'équipe qui s'en chargeait à la main n'existe plus.

Le cluster sait désormais en fabriquer à la demande : la classe **`local-path`**
est installée. Mais elle efface le volume quand sa revendication disparaît, et
l'équipe des archives veut garder ses données. Il lui faut sa propre classe.

## Ce que vous devez obtenir

1. Une StorageClass **`garde`**, servie par le **même provisionneur** que
   `local-path`, qui **garde** ses volumes quand leur revendication disparaît
   (`reclaimPolicy` **`Retain`**) et ne les crée qu'au moment où un Pod utilise
   la revendication (`volumeBindingMode` **`WaitForFirstConsumer`**). La classe
   `local-path` reste en place.

2. La revendication `donnees`, qui garde son nom, son namespace et sa taille,
   désigne la classe **`garde`**.

3. Elle est **liée**, et le volume auquel elle est liée a été **créé pour elle**
   par le provisionneur : personne ne l'a préparé d'avance.

4. Ce volume porte la **reclaim policy** que `garde` lui impose : **`Retain`**.

5. Un Pod nommé **`registre`** monte cette revendication sur **`/data`**.

6. Il y écrit un fichier **`/data/temoin`**, dans le volume.

## Les repères utiles

Commencez par regarder ce que le cluster propose, et ce que la revendication
demande. L'écart est là.

Une StorageClass ne fabrique rien elle-même : elle désigne un **provisionneur**,
et lui transmet ses réglages. Deux classes peuvent donc partager le même
provisionneur avec des politiques différentes. La classe existante vous dit
lequel employer.

Le champ de la revendication en cause vaut actuellement une **chaîne vide**, ce
qui n'est pas la même chose qu'un champ absent : la chaîne vide **désactive
explicitement** le provisionnement à la demande. Ce champ **ne se modifie pas**
sur une revendication existante.

Ne vous étonnez pas qu'elle reste en attente juste après votre correction : une
classe en `WaitForFirstConsumer` ne provisionne **qu'au moment où un Pod
utilise** la revendication.

## Comment vous saurez que c'est bon

Chaque test vérifie un des six états ci-dessus. Le premier vérifie aussi que
`local-path` existe toujours : renommer la classe existante n'est pas en créer
une. Le troisième ne se contente pas de voir la revendication liée : il vérifie
que le provisionneur a créé le volume pour cette revendication. Créer un volume
à la main, même avec la bonne classe, lierait aussi la revendication, sans rien
avoir provisionné à la demande. C'est le lab voisin, pas celui-ci.

```bash
dsoxlab check cka-storageclass-provisionnement-dynamique
```
