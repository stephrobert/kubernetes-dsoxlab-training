# Challenge : Lire l'état d'un Pod en erreur

## 📍 La situation

Dans le namespace **`diagnostic`** du cluster kind `lab`, trois applications
ont été lancées. **`web`** marche. **`api`** et **`batch`** ne démarrent pas.

Avant de corriger quoi que ce soit, l'équipe veut savoir **pourquoi**, avec
des preuves lues dans le cluster. Une correction faite à l'aveugle effacerait
la panne qu'il fallait comprendre.

Votre kubectl vise déjà ce cluster. Le répertoire **`~/diagnostic`** existe et
il est vide.

## 🎯 Ce que vous devez obtenir

1. Un fichier **`~/diagnostic/api.txt`** qui donne la **raison** pour laquelle
   le conteneur de `api` attend, et l'**image** en cause.

2. Un fichier **`~/diagnostic/batch.txt`** qui recopie le **message d'erreur**
   écrit par `batch` avant de s'arrêter, et le **code de sortie** de son
   dernier arrêt, écrit sous la forme `code de sortie : N`.

3. Un fichier **`~/diagnostic/top.txt`** qui donne le nom du **Pod** du
   namespace qui utilise le plus de **mémoire**.

4. **Rien n'est réparé** : `api` et `batch` gardent leur image et leur commande
   de départ.

## 🧭 Les repères utiles

Le statut d'un Pod dit qu'il va mal, pas pourquoi. Pour la raison, lisez
l'état du conteneur et les événements avec `kubectl describe`. Pour ce que le
programme a écrit, lisez ses journaux avec `kubectl logs`. Si le conteneur a
redémarré, le message utile est souvent dans l'exécution **d'avant**
(`--previous`).

`kubectl top` mesure la mémoire. metrics-server est déjà installé. Un Pod qui
ne tourne pas n'a pas de mesure.

## ✅ Comment vous saurez que c'est bon

Les tests comparent vos trois fichiers à ce que dit le cluster : la raison de
l'attente, le vrai code de sortie, la mémoire mesurée au moment du contrôle.
Ils vérifient aussi que les deux Deployments n'ont pas été modifiés.

```bash
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```
