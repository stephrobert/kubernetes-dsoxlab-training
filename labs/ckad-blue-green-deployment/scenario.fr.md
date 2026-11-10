# Basculer le trafic d'une version à l'autre : blue-green

## La situation

Dans le namespace **`lab`**, l'équipe veut livrer une nouvelle version de
son application sans la moindre coupure et avec un retour arrière
instantané. La méthode retenue : deux versions qui tournent **en même
temps**, `blue` en production et `green` prête à prendre le relais, et un
seul Service, **`app-prod`**, qui décide laquelle reçoit le trafic.

Pour que la bascule se voie, chaque version répond avec son nom. Un Pod
**`client`** est déjà là pour l'interroger : c'est l'instrument de mesure de
ce lab, pas une partie de ce qui est à construire, donc n'y touchez pas.

## Ce que vous devez obtenir

1. Un Deployment **`app-blue`** avec 2 replicas disponibles, dont les Pods
   portent les labels `app=myapp` et `version=blue`, et dont **chacun répond
   `blue` en HTTP sur le port 8080**.

2. Un Deployment **`app-green`** avec 2 replicas disponibles, labels
   `app=myapp` et `version=green`, dont chaque Pod répond `green` sur le même
   port.

3. Un Service **`app-prod`** qui écoute sur le port **8080**, et dont le
   selector nomme **à la fois** `app=myapp` et `version=green`.

4. Les endpoints de `app-prod` sont **exactement** les Pods green prêts, et
   depuis `client`, **toutes** les requêtes vers `http://app-prod:8080/`
   répondent `green`.

Relisez le point 1 : il est mesuré **après** la bascule. `app-blue` doit
encore être debout et répondre encore `blue` au moment du contrôle. Ce n'est
pas un détail, c'est tout le sujet du blue-green : le retour arrière n'est
instantané que parce que l'ancienne version n'a jamais cessé de servir.

## Les repères utiles

Un serveur qui répond son nom tient en une ligne de busybox : `httpd -f`
sert un répertoire, et un `echo` dans `index.html` avant de le lancer
suffit. Un conteneur qui ne fait que dormir porte les bons labels et ne sert
rien.

Dans la vraie vie, on crée `app-prod` en visant blue, on l'observe, puis on
le bascule vers green. Les tests mesurent l'état final, rien ne vous oblige
donc à passer par cette étape intermédiaire ; la trace que la méthode laisse,
c'est blue encore debout et encore servante.

Le selector d'un Service se change en place, et les endpoints suivent en
quelques secondes : c'est toute la bascule, et c'est aussi le retour
arrière.

## Comment vous saurez que c'est bon

Les tests lisent les deux Deployments et les labels de leurs Pods,
interrogent **chaque Pod sur sa propre adresse** pour vérifier qu'il sert sa
version, puis lisent le selector et les endpoints du Service, et font enfin
six requêtes depuis `client`.

```bash
dsoxlab check ckad-blue-green-deployment
```
