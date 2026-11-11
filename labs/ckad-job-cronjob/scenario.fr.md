# Un Job à complétions parallèles et un CronJob

## La situation

Dans le namespace **`lab`**, l'équipe a deux besoins de traitement par lots.

Le premier est ponctuel : un traitement qui doit s'exécuter **quatre fois**
avec succès, **deux exécutions à la fois**, et pas plus, parce que la base
de données derrière n'en supporte pas davantage. Chaque exécution dure une
dizaine de secondes.

Le second est récurrent : un nettoyage à lancer **toutes les cinq minutes**,
dont on veut garder la trace des **trois dernières** exécutions réussies et
de la **dernière** exécution échouée, pas plus, pour ne pas encombrer le
namespace.

## Ce que vous devez obtenir

1. Un Job **`batch-job`** dans `lab`, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, qui exécute
   quatre complétions, deux en parallèle, chaque exécution durant au moins
   dix secondes avant de réussir.

2. Le Job **terminé avec succès**, ses quatre Pods en `Succeeded`, et la
   preuve que deux d'entre eux ont tourné **en même temps**.

3. Un CronJob **`log-cleanup`** dans `lab`, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, planifié
   **toutes les cinq minutes**, qui conserve trois Jobs réussis et un Job
   échoué.

4. Un Job lancé **à la main depuis `log-cleanup`**, sans attendre sa
   prochaine échéance, terminé avec succès.

## Les repères utiles

Un Job décrit combien de fois réussir, et combien à la fois. Ses Pods
restent après la fin, avec leurs dates de début et de fin : c'est ainsi
qu'on sait ce qui s'est réellement chevauché.

Un CronJob n'est qu'un moule à Jobs sur un calendrier cron, avec deux
compteurs d'historique. Il ne lancera rien avant sa prochaine échéance, qui
peut être loin : pour l'éprouver tout de suite, on crée un Job à partir de lui.

## Comment vous saurez que c'est bon

Les tests lisent le Job, ses Pods et leurs horodatages, le CronJob, puis le
Job lancé à la main depuis lui.

```bash
dsoxlab check ckad-job-cronjob
```
