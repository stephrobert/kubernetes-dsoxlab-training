# Challenge : Isoler une application dans un namespace

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Un collègue a déployé l'application **`inventaire`** (un Deployment de
deux Pods et son Service sur le port 8080) en oubliant `-n` : elle est dans
**`default`**. Le namespace **`stock`**, qui devait la recevoir, est vide. Dans
le namespace **`caisse`**, le Pod **`caisse`** tourne : c'est lui qui doit
joindre l'inventaire. Le fichier **`~/namespaces/releve.txt`** attend ce que
vous observerez.

## 🎯 Ce que vous devez obtenir

1. Le Deployment **`inventaire`** et son Service **`inventaire`** sont dans
   **`stock`**, avec la même image et la même commande que ceux de `default`,
   sur le port 8080. Plus **rien** ne s'appelle `inventaire` dans `default`.

2. Depuis le Pod `caisse`, l'inventaire répond par son **nom suivi du
   namespace**, sur le chemin `/hostname` du port 8080. Ce chemin rend le nom
   du Pod qui répond. Après **`pod-qui-repond`**, dans le fichier : ce nom.

3. Depuis ce même Pod, le **nom court** `inventaire` échoue. Après
   **`nom-court`**, dans le fichier : ce que vous avez constaté.

## 🧭 Les repères utiles

Un objet ne change pas de namespace : on le recrée dans le bon, puis on retire
l'ancien. `kubectl get deployment inventaire -o yaml` montre l'image et la
commande à reprendre.

Le nom court d'un Service ne se trouve que dans le namespace du Pod qui le
cherche. Une requête qui doit échouer se lance avec un délai court, pour ne
pas attendre.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les objets de `stock` et de `default` et votre fichier, puis
rejouent les deux requêtes depuis le Pod `caisse`.

```bash
dsoxlab check k8s-isoler-par-namespace
```
