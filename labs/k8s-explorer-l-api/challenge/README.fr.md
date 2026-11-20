# Challenge : Explorer l'API avec api-resources et explain

## 📍 La situation

Le cluster kind **`lab`** tourne sur la machine, et votre kubectl le vise déjà.
L'équipe des données y a ajouté un **nouveau type d'objet** pour décrire ses
exports de bases. Personne ne vous l'a documenté : seul le cluster peut vous
dire comment il s'écrit.

Dans le namespace **`entrepot`**, le Deployment **`annuaire`** tourne sans
sonde de disponibilité. Le répertoire **`~/entrepot/`** attend votre relevé.

## 🎯 Ce que vous devez obtenir

1. Le fichier **`~/entrepot/releve.txt`** donne, sur deux lignes au format
   `clé: valeur`, ce qu'on écrit en tête d'un manifeste de ce type d'export :

   ```text
   apiversion: <groupe/version>
   kind: <Kind>
   ```

2. Un export nommé **`ventes-hebdo`** existe dans `entrepot`. Il exporte la
   base **`ventes`** **au format parquet**, **chaque lundi à 3 h 30**. À vous
   de trouver dans le cluster le nom des champs et le format attendu.

3. **`annuaire`** a une **sonde de disponibilité HTTP** qui interroge le chemin
   **`/healthz`** sur le **port nommé `web`** de son conteneur, et tous ses
   Pods sont prêts (Ready).

4. Le relevé a une troisième ligne, **`inventaire:`**, qui nomme **chaque type
   d'objet présent dans `entrepot`**, séparés par des virgules. Inutile d'y
   mettre les événements.

## 🧭 Les repères utiles

Un type peut être servi en plusieurs versions, qui n'ont pas forcément les
mêmes champs. Le nom d'un groupe ne dit pas sa version : c'est
`kubectl api-resources` qui donne celle que le cluster sert. Un type inconnu se
découvre comme un type connu : sa ligne dans `api-resources`, puis ses champs
avec `kubectl explain`. La mention `-required-` signale un champ obligatoire,
une ligne `enum:` les seules valeurs permises, et la description d'un champ dit
son format.

La sonde se trouve de la même façon, en descendant dans le modèle de Pod du
Deployment. Modifiez `annuaire` lui-même, sans le supprimer.

`kubectl get all` ne montre pas tout ce que contient un namespace. Pour
l'inventaire, interrogez chaque type que le cluster déclare listable dans un
namespace.

## ✅ Comment vous saurez que c'est bon

Les tests comparent votre relevé à ce que déclare le cluster, puis lisent
l'export et la sonde dans le cluster.

```bash
dsoxlab check k8s-explorer-l-api
```
