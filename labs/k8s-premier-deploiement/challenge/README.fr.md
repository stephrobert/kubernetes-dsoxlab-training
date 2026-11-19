# Challenge : Déployer, exposer et mettre à l'échelle une première application

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Le namespace **`demo-app`** n'existe pas encore. Le répertoire
**`~/demo-app/`** est vide : il attend la réponse de votre application.

## 🎯 Ce que vous devez obtenir

1. Dans le namespace **`demo-app`**, un Deployment **`nginx`** qui lance
   l'image de la leçon :
   `nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.

2. Le Deployment `nginx` a d'abord été créé avec **un seul Pod**, puis passé à
   **trois Pods disponibles**.

3. Un Service **`nginx`** de type ClusterIP, sur le port **80**, qui trouve
   **les trois Pods**.

4. Un fichier **`~/demo-app/reponse.html`** qui contient la page renvoyée par
   `http://nginx`, demandée depuis un Pod du namespace `demo-app`.

## 🧭 Les repères utiles

Créez d'abord le namespace. Ajoutez ensuite `-n demo-app` à chaque commande :
sans cette option, vos objets vont dans le namespace `default`.

Un Service ne prévient pas quand il ne trouve aucun Pod. Si l'application ne
répond pas, comparez le `Selector` du Service aux étiquettes des Pods, et
regardez ses endpoints après le passage à trois Pods.

Le nom `nginx` d'un Service n'existe qu'à l'intérieur du cluster. Pour le
joindre, lancez un Pod temporaire avec une image qui sait faire une requête
web. Sa réponse s'écrit dans un fichier avec `>`, comme pour n'importe quelle
commande.

## ✅ Comment vous saurez que c'est bon

Les tests regardent le Deployment, le Service et ses endpoints. Ils comparent
ensuite votre fichier à la page que sert vraiment nginx.

```bash
dsoxlab check k8s-premier-deploiement
```
