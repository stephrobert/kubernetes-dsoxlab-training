# Livrer un manifeste robuste à partir d'un cahier des charges

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, l'équipe des
expéditions vous confie son application **`colis`**, un serveur web, à livrer
dans le namespace **`expedition`** en deux variantes, **dev** et **prod**. Au même
moment, le Pod **`etiquettes`** de ce namespace ne démarre plus. Le répertoire
**`~/expedition/`** est vide. Le cahier des charges dit ce qu'il faut obtenir,
pas comment.

Les images :

```text
application : nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
outillage   : busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Le cahier des charges

1. **Une base Kustomize unique**, dans `~/expedition/base/`, et deux overlays,
   `~/expedition/overlays/dev/` et `~/expedition/overlays/prod/`. Ils ne
   diffèrent que par le **nombre de réplicas** (1 en dev, 3 en prod), le
   **préfixe des noms** (`dev-`, `prod-`) et le label **`env`** (`dev`, `prod`).
   Les deux variantes vivent dans `expedition` : le Deployment de prod s'appelle
   donc **`prod-colis`**.
2. **`prod-colis`** a ses **3 réplicas disponibles**, sur l'image de l'application
   **référencée par digest**.
3. Chaque Pod de l'application porte un **init container** qui prépare la page
   d'accueil et se termine avant le démarrage du serveur, et un **sidecar natif**
   dont les journaux reprennent, ligne à ligne, les accès que le serveur écrit
   sur un **volume partagé** (le serveur écrit ses accès dans
   `/var/log/nginx/access.log`).
4. **Chaque conteneur** déclare ses requests et ses limits ; la **limite de
   mémoire** du serveur vaut **`128Mi`**.
5. Les sondes de **démarrage**, de **vivacité** et de **disponibilité**
   interrogent le serveur en HTTP sur son **port 80**, et chaque Pod est **Ready
   sans redémarrage**.
6. Un CronJob **`purge-colis`** tourne **chaque jour à 3 h**, garde **deux** Jobs
   réussis et **un** échoué, et n'exécute **jamais deux purges en même temps**.
7. Un Job **`inventaire`** est **terminé** avec **trois complétions**. Le
   CronJob et le Job **ne font pas partie des variantes** : appliquez-les à
   part, sous ces noms exacts.
8. **Le cluster correspond au dossier** : comparer chaque overlay au cluster ne
   trouve aucune différence.
9. **Avant toute réparation**, écrivez dans **`~/expedition/cause.txt`**
   pourquoi **`etiquettes`** ne démarre pas : ce qu'il cherche sans le trouver,
   par son nom, et que cela manque. Ensuite, n'y touchez plus.
10. **`etiquettes`** tourne de nouveau, **sans avoir été recréé**. Il attend la
    valeur **`FORMAT=A6`**.

## Comment vous serez noté

Le challenge est noté sur l'**état final** du cluster et de vos fichiers, jamais
sur les commandes tapées. Les **dix exigences pèsent toutes autant**. Le seuil
est de **70 sur 100**, et **trois exigences sont bloquantes** : elles doivent
réussir quel que soit le total. Ce sont `prod-colis` disponible sur son digest
(exigence 2), les sondes avec des Pods Ready sans redémarrage (exigence 5), et
la cause consignée avant la réparation (exigence 9).

Quatre **indices** sont proposés, et chacun retire des points du barème avant
le calcul de la note : 2, 3, 5 puis 5, soit 15 au plus. Avec les quatre, dix
exigences réussies donnent 85, neuf en donnent 76, et huit en donnent 68, sous
le seuil. Sans indice, sept exigences suffisent tout juste (70) ; avec le
premier indice, elles n'en donnent plus que 69.

Aucune procédure n'est donnée : les leçons du module ont tout enseigné.

```bash
dsoxlab check  k8s-challenge-manifest-robuste
dsoxlab submit k8s-challenge-manifest-robuste
```
