# Garder des données au-delà de la vie d'un Pod

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, l'équipe des
archives veut que son application **`registre`** garde ses données quand son Pod
disparaît. Elle vit dans le namespace **`archives`**. On y trouve déjà une
revendication, **`journal-ancien`**, posée par une autre équipe : elle reste
**Pending** depuis sa création. Le répertoire **`~/archives/`** est vide. Le
cahier des charges dit ce qu'il faut obtenir, pas comment.

L'image de l'application :

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Le cahier des charges

1. Une StorageClass **`conserve`**, servie par le provisionneur que le cluster
   utilise déjà pour sa classe par défaut. La revendication **`registre-donnees`**,
   dans `archives`, la désigne et demande **`256Mi`** en **`ReadWriteOnce`**. Elle
   est **Bound** à un volume que ce provisionneur a **créé pour elle** : aucun
   volume préparé d'avance.
2. Un Deployment **`registre`**, à un réplica, monte `registre-donnees` sur
   **`/var/lib/registre`**. Le fichier témoin **`/var/lib/registre/temoin.txt`**
   porte, en **première ligne**, le **nom du Pod qui l'a écrit**.
3. Supprimez ce Pod. Le Pod que le Deployment recrée relit le témoin **intact** :
   même contenu, jamais réécrit depuis.
4. Le volume de `registre-donnees` garde ses données si la revendication
   disparaît : sa **reclaim policy** est **`Retain`**, lue sur le
   PersistentVolume.
5. **Avant toute correction**, écrivez dans **`~/archives/cause.txt`** pourquoi
   **`journal-ancien`** reste Pending : ce qu'elle demande sans le trouver, par
   son nom, et que cela manque. Ensuite, n'y touchez plus.
6. **`journal-ancien`** est **Bound**, et demande toujours **`100Mi`**.

## Comment vous serez noté

Le challenge est noté sur l'**état final** du cluster et de vos fichiers, jamais
sur les commandes tapées. Les **six exigences pèsent toutes autant**. Le seuil
est de **70 sur 100**, et **trois exigences sont bloquantes** : elles doivent
réussir quel que soit le total. Ce sont le volume créé pour `registre-donnees`
par la classe (exigence 1), le témoin relu intact (exigence 3), et la cause
consignée avant la correction (exigence 5).

Quatre **indices** sont proposés, et chacun retire des points du barème avant
le calcul de la note : 2, 3, 5 puis 5, soit 15 au plus. Sans indice, six
exigences donnent 100 et cinq en donnent 83. Avec les quatre, six exigences
donnent 85 et cinq en donnent 71, encore au-dessus du seuil. Quatre exigences
ne suffisent jamais : 67 au mieux.

Aucune procédure n'est donnée : les leçons du module ont tout enseigné.

```bash
dsoxlab check  k8s-challenge-donnees-qui-survivent
dsoxlab submit k8s-challenge-donnees-qui-survivent
```
