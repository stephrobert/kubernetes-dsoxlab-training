# Lire l'état d'un Pod en erreur

## La situation

Dans le namespace **`diagnostic`** du cluster kind `lab`, trois applications
ont été lancées. **`web`** répond. **`api`** et **`batch`** ne démarrent pas.
Avant de corriger quoi que ce soit, l'équipe veut savoir **pourquoi**, preuves
lues dans le cluster : une correction faite à l'aveugle efface la panne qu'il
fallait comprendre.

Votre `kubectl` est déjà réglé sur ce cluster. Le répertoire
**`~/diagnostic`** existe et est vide.

## Ce que vous devez obtenir

1. Un fichier **`~/diagnostic/api.txt`** qui nomme la **raison** pour laquelle
   le conteneur de `api` attend, et l'**image** fautive.

2. Un fichier **`~/diagnostic/batch.txt`** qui cite l'**erreur** que `batch` a
   écrite avant de s'arrêter, et le **code de sortie** de son dernier conteneur
   terminé, écrit sous la forme `code de sortie : N`.

3. Un fichier **`~/diagnostic/top.txt`** qui nomme le **Pod** du namespace qui
   consomme le plus de **mémoire**.

4. **Rien n'est réparé** : `api` et `batch` gardent leur image et leur commande
   d'origine.

## Les repères utiles

Un statut ne suffit pas : il dit qu'un Pod va mal, pas pourquoi. L'état
détaillé d'un conteneur, sa raison et les événements du Pod disent ce qui
bloque ; les journaux disent ce que le programme a écrit avant de s'arrêter.
Quand un conteneur a été relancé, les journaux utiles sont souvent ceux de
l'exécution **précédente**.

Les mesures de consommation viennent de metrics-server, déjà installé. Un Pod
qui ne tourne pas n'a pas de mesure.

## Comment vous saurez que c'est bon

Les tests confrontent vos trois fichiers à ce que le cluster dit lui-même :
raison d'attente, code de sortie réel, mémoire mesurée au moment du contrôle.
Ils vérifient aussi que les deux Deployments n'ont pas été modifiés.

```bash
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```
