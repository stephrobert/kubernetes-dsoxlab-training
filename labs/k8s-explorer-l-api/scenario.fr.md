# Explorer l'API avec api-resources et explain

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, l'équipe
d'exploitation a installé un **nouveau type de ressource** pour décrire ses
sauvegardes, et vous n'avez **aucune documentation** : l'API du cluster est votre
seule source. Dans le namespace **`archives`**, le Deployment **`catalogue`**
tourne sans sonde de disponibilité. Le répertoire **`~/archives/`** attend votre
relevé.

## Ce que vous devez obtenir

1. **`~/archives/releve.txt`** donne, sur deux lignes `clé: valeur`, ce qu'il faut
   écrire dans un manifeste de ce type de sauvegarde :

   ```text
   apiversion: <groupe/version>
   kind: <Kind>
   ```

2. Une sauvegarde nommée **`commandes-nuit`** existe dans `archives` : elle
   sauvegarde la base **`commandes`** **chaque jour à 2 h 00**. Les noms et le
   format des champs sont à trouver dans l'API.

3. **`catalogue`** porte une **sonde de disponibilité HTTP** qui interroge la
   **racine du port 80**, et ses Pods sont Ready.

4. Le relevé porte une troisième ligne, **`inventaire:`**, qui nomme **chaque type
   d'objet présent dans `archives`**, séparés par des virgules. Les événements
   ne sont pas exigés.

## Les repères utiles

Le nom d'un groupe ne dit pas sa version : c'est l'API qui la donne. Un type que
vous ne connaissez pas se découvre comme un type standard, colonne par colonne,
puis champ par champ : la mention `-required-` signale ce qu'un objet ne peut pas
omettre, et la description d'un champ dit son format.

La sonde se trouve de la même façon, en descendant dans le Pod template du
Deployment. Corrigez `catalogue` en place.

`kubectl get all` ne liste pas tout ce que contient un namespace. Pour
l'inventaire, interrogez chaque type que l'API déclare comme listable dans un
namespace.

## Comment vous saurez que c'est bon

Les tests confrontent votre relevé à ce que l'API du cluster déclare, puis lisent
la sauvegarde et la sonde dans le cluster.

```bash
dsoxlab check k8s-explorer-l-api
```
