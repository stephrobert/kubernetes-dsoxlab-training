# Étiqueter et sélectionner des Pods

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Dans le namespace **`etiquettes`**, deux Deployments tournent :
**`web`**, à trois réplicas, et **`api`**, à deux. Aucun de leurs Pods ne porte
de label `env`.

Le relevé **`~/etiquettes/releve.txt`** attend un sélecteur.

## Ce que vous devez obtenir

1. **Tous les Pods de `web` portent le label `env=prod`**, et ils le gardent
   quand ils sont remplacés.

2. **Le Deployment `web` porte une annotation `description`**, avec une phrase
   qui dit à quoi il sert.

3. **`selecteur`** contient un sélecteur de labels qui utilise une négation
   (`!=` ou `!clé`) et qui rend **exactement les Pods de `api`**.

## Les repères utiles

Un label posé sur un Pod vit et meurt avec ce Pod. Les Pods d'un Deployment
sont remplacés à chaque mise à jour, à chaque suppression, à chaque panne de
nœud : un label qui doit durer s'écrit là d'où les Pods sont fabriqués. Un
label posé sur le Deployment lui-même, lui, ne descend pas jusqu'aux Pods.

Avant de décider entre label et annotation, posez-vous la question qui tranche :
faudra-t-il un jour sélectionner des objets par cette information ? Une phrase
de description ne sert pas à sélectionner, et un label n'accepte pas d'espaces.

Pour le sélecteur, essayez-le avec `kubectl get pods -n etiquettes -l` avant
de le consigner, et comptez ce qu'il rend : une négation retient aussi les
objets qui n'ont pas du tout la clé.

## Comment vous saurez que c'est bon

Les tests lisent le modèle de Pod et les annotations de `web`, puis rejouent
votre sélecteur tel quel.

```bash
dsoxlab check k8s-labels-et-selecteurs
```
