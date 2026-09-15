# Basculer le trafic d'une version à l'autre : blue-green

## La situation

Dans le namespace **`lab`**, l'équipe veut livrer une nouvelle version de
son application sans la moindre coupure et avec un retour arrière
instantané. La méthode retenue : deux versions qui tournent **en même
temps**, `blue` en production et `green` prête à prendre le relais, et un
seul Service, **`app-prod`**, qui décide laquelle reçoit le trafic.

Pour que la bascule se voie, chaque version répond avec son nom. Un Pod
**`client`** est là pour l'interroger.

## Ce que vous devez obtenir

1. Un Deployment **`app-blue`** à 2 replicas, dont les Pods portent les
   labels `app=myapp` et `version=blue`, et répondent `blue` en HTTP sur le
   port 8080.

2. Un Deployment **`app-green`** à 2 replicas, labels `app=myapp` et
   `version=green`, qui répond `green` sur le même port.

3. Un Service **`app-prod`**, port 8080, qui vise d'abord la version blue.

4. La bascule : `app-prod` vise la version green. Ses endpoints sont
   exactement les Pods green, et depuis `client`, **toutes** les requêtes
   vers `http://app-prod:8080/` répondent `green`.

## Les repères utiles

Un serveur qui répond son nom tient en une ligne de busybox : `httpd -f`
sert un répertoire, et un `echo` dans `index.html` avant de le lancer
suffit.

Le selector d'un Service se change en place, et les endpoints suivent en
quelques secondes : c'est toute la bascule, et c'est aussi le retour
arrière.

## Comment vous saurez que c'est bon

Les tests lisent les deux Deployments, le selector et les endpoints du
Service, et font plusieurs requêtes depuis `client`.

```bash
dsoxlab check ckad-blue-green-deployment
```
