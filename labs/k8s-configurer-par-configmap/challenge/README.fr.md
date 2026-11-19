# Challenge : Configurer une application par ConfigMap

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Le namespace **`configuration`** est vide.

## 🎯 Ce que vous devez obtenir

Dans le namespace `configuration`, avec les valeurs de la leçon :

1. Un ConfigMap **`app-config`** porte `APP_MODE=production` et `LOG_LEVEL`. Un
   Deployment **`app`** (busybox 1.38.0, qui dort) reçoit ces deux clés en
   **variables d'environnement**, et `APP_MODE` se lit dans le Pod.

2. Un ConfigMap **`app-fichier`** porte un fichier **`app.properties`**, monté
   **en dossier** sur **`/etc/app`** dans le conteneur. Après modification, ce
   fichier dit **`mode=maintenance`**, et le fichier lu dans le Pod est à jour.

3. `LOG_LEVEL`, d'abord à `info`, passe à **`debug`** dans `app-config`. Le
   Deployment est ensuite **redémarré**, et le Pod voit `debug`.

4. **Aucune valeur** n'est écrite directement dans le Deployment.

## 🧭 Les repères utiles

Créez les ConfigMaps avant le Deployment : `--from-literal` pour des valeurs,
`--from-file` pour un fichier, dont le nom devient la clé. Vérifiez toujours
depuis le conteneur, avec `kubectl exec deploy/app --` : la spécification dit
ce qui est demandé, le conteneur dit ce qui est vu.

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
