# Déployer, exposer et mettre à l'échelle une première application

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Le namespace **`demo-app`** n'existe pas encore. Le répertoire
**`~/demo-app/`** attend la réponse HTTP de votre application.

## Ce que vous devez obtenir

1. Dans le namespace **`demo-app`**, un Deployment **`nginx`** tourne sur
   l'image épinglée de la leçon :
   `nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.

2. `nginx` a été créé avec **un réplica**, puis **mis à l'échelle** : il a
   maintenant **trois réplicas disponibles**.

3. Un Service **`nginx`** de type ClusterIP l'expose sur le port 80, et compte
   **trois endpoints prêts**.

4. **`~/demo-app/reponse.html`** contient la réponse de `http://nginx`, lue
   **depuis un Pod client** du namespace.

## Les repères utiles

Créez d'abord le namespace, puis travaillez dedans : sans `-n demo-app`, les
objets partent dans `default`. Un Deployment crée un ReplicaSet, qui crée les
Pods ; la colonne READY de `kubectl get deployment` compte les Pods prêts.

Un Service ne vérifie pas qu'il trouve des Pods : une liste d'endpoints vide ne
lève aucune erreur. Comparez son Selector aux labels des Pods, et regardez ses
endpoints après la mise à l'échelle.

Le nom d'un Service se résout dans le cluster, pas sur la machine. Un Pod
temporaire, lancé avec une image qui sait faire une requête HTTP et supprimé à
la fin, peut l'interroger ; sa sortie se redirige dans un fichier comme toute
autre.

## Comment vous saurez que c'est bon

Les tests lisent le Deployment, le Service et ses endpoints, puis comparent
votre fichier à la page que sert vraiment nginx.

```bash
dsoxlab check k8s-premier-deploiement
```
