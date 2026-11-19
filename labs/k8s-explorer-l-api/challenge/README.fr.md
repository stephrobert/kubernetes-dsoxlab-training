# Challenge : Explorer l'API avec api-resources et explain

## 📍 La situation

Le cluster kind **`lab`** tourne sur la machine, et votre kubectl le vise déjà.
L'équipe d'exploitation y a ajouté un **nouveau type d'objet** pour décrire ses
sauvegardes. Personne ne vous l'a documenté : seul le cluster peut vous dire
comment il s'écrit.

Dans le namespace **`archives`**, le Deployment **`catalogue`** tourne sans
sonde de disponibilité. Le répertoire **`~/archives/`** attend votre relevé.

## 🎯 Ce que vous devez obtenir

1. Le fichier **`~/archives/releve.txt`** donne, sur deux lignes au format
   `clé: valeur`, ce qu'on écrit en tête d'un manifeste de ce type de
   sauvegarde :

   ```text
   apiversion: <groupe/version>
   kind: <Kind>
   ```

2. Une sauvegarde nommée **`commandes-nuit`** existe dans `archives`. Elle
   sauvegarde la base **`commandes`** **chaque jour à 2 h 00**. À vous de
   trouver dans le cluster le nom des champs et le format attendu.

3. **`catalogue`** a une **sonde de disponibilité HTTP** qui interroge la
   **racine (`/`) du port 80**, et tous ses Pods sont prêts (Ready).

4. Le relevé a une troisième ligne, **`inventaire:`**, qui nomme **chaque type
   d'objet présent dans `archives`**, séparés par des virgules. Inutile d'y
   mettre les événements.

## 🧭 Les repères utiles

Le nom d'un groupe ne dit pas sa version : c'est `kubectl api-resources` qui la
donne. Un type inconnu se découvre comme un type connu : sa ligne dans
`api-resources`, puis ses champs avec `kubectl explain`. La mention
`-required-` signale un champ obligatoire, et la description d'un champ dit
son format.

La sonde se trouve de la même façon, en descendant dans le modèle de Pod du
Deployment. Modifiez `catalogue` lui-même, sans le supprimer.

`kubectl get all` ne montre pas tout ce que contient un namespace. Pour
l'inventaire, interrogez chaque type que le cluster déclare listable dans un
namespace.

## ✅ Comment vous saurez que c'est bon

Les tests comparent votre relevé à ce que déclare le cluster, puis lisent la
sauvegarde et la sonde dans le cluster.

```bash
dsoxlab check k8s-explorer-l-api
```
