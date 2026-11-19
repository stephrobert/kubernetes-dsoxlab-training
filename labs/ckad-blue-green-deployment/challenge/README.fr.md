# Challenge : Livrer une nouvelle version sans coupure, en blue-green

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`lab`**, l'équipe veut livrer une nouvelle
version de son application sans aucune coupure, et pouvoir revenir en arrière
tout de suite.

La méthode choisie :

- deux versions tournent **en même temps** : `blue` en production, `green`
  prête à prendre le relais ;
- un seul Service, **`app-prod`**, décide laquelle reçoit le trafic.

Pour qu'on voie la bascule, chaque version répond son nom. Un Pod **`client`**
est déjà là pour interroger le Service. Il sert à mesurer le résultat : n'y
touchez pas.

## 🎯 Ce que vous devez obtenir

1. Un Deployment **`app-blue`** avec 2 Pods disponibles. Ses Pods ont les
   labels `app=myapp` et `version=blue`, et **chacun répond `blue` en HTTP sur
   le port 8080**.

2. Un Deployment **`app-green`** avec 2 Pods disponibles, labels `app=myapp`
   et `version=green`. Chacun répond `green`, sur le même port.

3. Un Service **`app-prod`** qui écoute sur le port **8080**. Son sélecteur
   demande **à la fois** `app=myapp` et `version=green`.

4. Les endpoints de `app-prod` sont **exactement** les Pods green prêts. Depuis
   `client`, **toutes** les requêtes vers `http://app-prod:8080/` répondent
   `green`.

Attention au point 1 : il est vérifié **après** la bascule. `app-blue` doit
donc encore tourner et répondre `blue` au moment du contrôle. C'est le principe
même du blue-green : le retour arrière n'est immédiat que parce que l'ancienne
version n'a jamais cessé de servir.

## 🧭 Les repères utiles

Un serveur qui répond son nom tient en une ligne de busybox : un `echo` dans
`index.html`, puis `httpd -f` pour servir le répertoire. Un conteneur qui ne
fait que dormir a les bons labels, mais ne sert rien.

En vrai, on crée d'abord `app-prod` vers blue, on l'observe, puis on le bascule
vers green. Les tests ne regardent que l'état final : vous n'êtes pas obligé de
passer par l'étape vers blue. Mais blue doit rester debout et continuer à
répondre.

Le sélecteur d'un Service se change sans le recréer, et les endpoints suivent
en quelques secondes. C'est toute la bascule, et c'est aussi le retour arrière.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les deux Deployments et les labels de leurs Pods. Ils
interrogent **chaque Pod sur sa propre adresse**, pour vérifier qu'il répond sa
version. Ils lisent ensuite le sélecteur du Service et ses endpoints, puis
envoient six requêtes depuis `client`.

```bash
dsoxlab check ckad-blue-green-deployment
```
