# Challenge : Configurer une application par ConfigMap

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Le namespace **`tarification`** est vide.

## 🎯 Ce que vous devez obtenir

Dans le namespace `tarification` :

1. Un ConfigMap **`tarifs-env`** porte `DEVISE=EUR` et `TAUX_TVA`. Un
   Deployment **`tarifs`** (busybox 1.38.0, qui dort) reçoit ces deux clés en
   **variables d'environnement**, et `DEVISE` se lit dans le Pod.

2. Un ConfigMap **`tarifs-grille`** porte un fichier **`grille.ini`**, monté
   **en dossier** sur **`/etc/tarifs`** dans le conteneur. Après modification,
   ce fichier contient la ligne **`remise=15`**, et le fichier lu dans le Pod
   est à jour.

3. `TAUX_TVA`, d'abord à `20`, passe à **`5.5`** dans `tarifs-env`. Le
   Deployment est ensuite **redémarré**, et le Pod voit `5.5`.

4. **Aucune valeur** n'est écrite directement dans le Deployment.

## 🧭 Les repères utiles

Créez les ConfigMaps avant le Deployment : `--from-literal` pour des valeurs,
`--from-file` pour un fichier, dont le nom devient la clé. Vérifiez toujours
depuis le conteneur, avec `kubectl exec deploy/tarifs --` : la spécification
dit ce qui est demandé, le conteneur dit ce qui est vu.

Après une modification, tout ne se met pas à jour de la même façon :

- une variable d'environnement se lit au démarrage du conteneur, puis reste
  figée ;
- un volume monté en dossier se met à jour tout seul, avec un délai ;
- un montage par `subPath` ne se met jamais à jour.

Le redémarrage du Deployment remplace les Pods, qui relisent tout.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les ConfigMaps et le Deployment, puis ce que voit le
conteneur.

```bash
dsoxlab check k8s-configurer-par-configmap
```
