# Challenge : Observer la lecture d'un fichier sensible avec Tetragon, puis la bloquer

## La situation

Dans le namespace **`comptes`**, une clé d'API est montée depuis le Secret
`cle-api`, en **`/etc/comptes/cle`**, dans deux Pods : **`rapport`** et
**`vitrine`**. L'équipe sécurité soupçonne l'un des deux de lire la clé
régulièrement, sans raison. Elle veut savoir lequel et avec quel outil, puis
empêcher toute lecture de la clé.

**Tetragon 1.8.0** est installé sur le cluster, avec un agent par nœud.

## Ce que vous devez obtenir

1. Tetragon **voit** les lectures de la clé : chaque ouverture d'un fichier sous
   `/etc/comptes/` produit un événement, avec le Pod et le binaire.

2. Un ConfigMap **`constat-tetragon`**, dans le namespace `comptes`, nomme :
   - `pod` : le Pod qui lit la clé de lui-même ;
   - `binaire` : le binaire qui la lit, tel que Tetragon le montre, en chemin
     complet (par exemple `/bin/exemple`).

3. Toute lecture de la clé est ensuite **bloquée** : le processus est tué.

4. Le blocage **ne vise que la clé** : les autres fichiers des Pods se lisent
   toujours.

## Les repères utiles

Tetragon écrit chaque événement en JSON dans le conteneur `export-stdout` de
son agent. Un agent ne voit que les Pods de **son** nœud.

`tetra getevents`, lancé dans un agent, ne montre que les événements à venir,
pas ceux déjà passés.

## Comment vous saurez que c'est bon

Les tests déclenchent eux-mêmes une lecture de la clé dans `vitrine`, puis
cherchent l'événement chez l'agent de son nœud. Le binaire qui lit la clé est
tiré au sort à la préparation : seul l'événement de Tetragon le révèle.

```bash
dsoxlab check k8s-observer-et-bloquer-avec-tetragon
```
