# Utiliser une ressource personnalisée, lire les refus de son schéma, la débloquer

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, l'équipe
d'exploitation a installé une CRD qui décrit des **sauvegardes** : le kind
**`Sauvegarde`**. Aucun opérateur ne la surveille encore. Dans le namespace
**`sauvegardes`**, on trouve deux ressources :

- **`hebdomadaire`**, qui garde ses sauvegardes **14 jours** ;
- **`ancienne`**, que quelqu'un a supprimée et qui reste pourtant affichée, en
  **Terminating**.

Le répertoire **`~/sauvegardes/`** attend ce que vous lirez de l'API.

## Ce que vous devez obtenir

1. Une Sauvegarde **`quotidienne`** dans `sauvegardes`, de source
   **`donnees-registre`**, gardée **7 jours**.
2. **`hebdomadaire`** garde désormais **30 jours**, **sans avoir été
   recréée**.
3. **`~/sauvegardes/api.txt`** donne le **groupe et la version d'API** qui
   servent le kind Sauvegarde, sous la forme `groupe/version`.
4. **`~/sauvegardes/refus.txt`** contient le **message de l'API** qui refuse une
   Sauvegarde gardée **400 jours**. Cette demande est refusée : elle ne crée
   rien.
5. **`ancienne`** a disparu, **sans** que la CRD ni les autres ressources aient
   été supprimées.

## Les repères utiles

Une CRD ajoute un kind à l'API, dans un groupe et une version qui lui sont
propres. La liste des ressources que l'API sert, et l'explication de leurs
champs, se lisent comme pour un kind natif.

Une ressource personnalisée se crée, se lit, se modifie et se supprime comme un
objet natif. Ses champs suivent le **schéma** de la CRD : un type faux ou une
valeur hors des bornes est refusé par l'API, qui dit pourquoi.

Une ressource qui reste en Terminating attend qu'on retire ses
**finalizers**. D'habitude, c'est son contrôleur qui le fait. Ici, il n'y en a
pas. Supprimer la CRD débloquerait la ressource, mais emporterait toutes les
autres avec elle.

## Comment vous saurez que c'est bon

Chaque test vérifie un des cinq états ci-dessus. Pour `hebdomadaire` et pour la
CRD, il compare leur identifiant à celui du départ. Pour le refus, il relit votre
fichier, puis vérifie que l'API refuse toujours une rétention de 400 jours.

```bash
dsoxlab check ckad-crd-ressource-personnalisee
```
