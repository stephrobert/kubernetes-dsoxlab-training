# Extraire des champs avec JSONPath et custom-columns

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Dans le namespace **`extraction`**, le Deployment **`web`** fait tourner
deux Pods nginx, label `app=web`. Une mise à jour de son image a été demandée,
mais son déploiement a été mis en pause.

Le relevé **`~/extraction/releve.txt`** attend une valeur, et le répertoire
**`~/extraction/`** vos deux listes.

## Ce que vous devez obtenir

1. **`image-modele`** donne l'image que demande le **modèle de Pod** du
   Deployment `web`, telle quelle, digest compris.

2. **`~/extraction/pods-jsonpath.txt`** liste, avec **JSONPath**, chaque Pod de
   `web` suivi du **nœud** qui l'héberge : une ligne par Pod, sans en-tête.

3. **`~/extraction/pods-colonnes.txt`** donne la même information avec
   **custom-columns** : une ligne d'en-tête, puis une ligne par Pod.

## Les repères utiles

Pour trouver le chemin d'un champ, affichez d'abord l'objet en YAML et suivez
l'indentation. Sur un seul objet, le chemin part de sa racine ; sur une liste,
les objets sont sous `.items`, et `range ... end` répète un motif pour chacun.
Sans `{"\n"}`, JSONPath n'écrit aucun retour à la ligne. Les guillemets
empêchent le shell d'interpréter crochets, accolades et virgules.

Le Deployment et ses Pods ne disent pas forcément la même chose : un
déploiement en pause a déjà changé son modèle, sans avoir encore remplacé ses
Pods. Ce qui est demandé ici, c'est ce que veut le Deployment.

Une sortie de kubectl se redirige dans un fichier comme toute autre.

## Comment vous saurez que c'est bon

Les tests comparent votre relevé et vos deux fichiers au Deployment et à ses
Pods.

```bash
dsoxlab check k8s-extraire-avec-kubectl
```
