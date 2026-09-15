# Capstone : livrer la boutique, à partir du seul cahier des charges

## La situation

On vous remet un cahier des charges, comme une équipe vous en remettrait un :
ce que la livraison doit satisfaire, pas la manière d'y arriver. Rien, plus
bas, ne nomme un objet Kubernetes. Les choisir est justement l'exercice.

Tout se passe dans le namespace **`boutique`**, qui existe déjà. Deux Pods
clients y tournent, `frontend` et `intrus`. **N'y touchez pas** : ils ne font
pas partie de la livraison, ils sont l'instrument avec lequel la dernière
exigence est mesurée.

Comptez environ **45 minutes**, et traitez cela comme l'épreuve : vous ne
finirez peut-être pas tout, et le seuil de réussite est de **66 %**. Quatre
exigences entièrement satisfaites valent mieux que six à moitié faites.

## Ce que la livraison doit satisfaire

1. **Le catalogue tourne en deux exemplaires**, sous le nom `catalogue`, à
   partir de l'image `nginxinc/nginx-unprivileged:1.27-alpine`. Si un
   exemplaire disparaît, un autre prend sa place.

2. **Le message d'accueil se change sans reconstruire l'image.** Le conteneur
   reçoit le texte `Bienvenue dans la boutique` dans la variable
   d'environnement `MESSAGE`, et cette valeur vit en dehors de la définition
   du Pod, sous le nom `catalogue-config`.

3. **Le mot de passe de la base n'apparaît dans aucun manifeste.** Il vaut
   `s3cr3t-boutique`, il est détenu sous le nom `catalogue-db` dans la clé
   `password`, et le conteneur le lit dans le fichier `/etc/db/password`.

4. **Le cluster sait quand envoyer du trafic, et quand redémarrer.** Deux
   contrôles sur le port HTTP du conteneur : l'un décide si un exemplaire
   reçoit du trafic, l'autre s'il faut le redémarrer. Aucun des deux ne doit
   faire tomber le Pod pendant que nginx démarre normalement.

5. **Le conteneur ne tourne pas en root**, et c'est le manifeste qui le dit,
   pas l'image. Son identifiant d'utilisateur est `101`.

6. **Seul le frontend entre.** Le catalogue répond au nom stable
   `catalogue-svc` sur le port `80` dans le namespace. Les Pods portant le
   label `role=frontend` peuvent le joindre ; rien d'autre dans le namespace
   ne le peut.

## Les repères utiles

Rien ici ne dit quel objet employer. Ce sont les pièges que ce capstone a
réellement attrapés.

- Un processus qui ne tourne pas en root ne peut pas ouvrir un port inférieur
  à 1024. Cette image écoute sur **8080**, pas sur 80. Le nom et le port de
  l'exigence 6 sont ce que voit le *client*, ce qui n'est pas forcément ce
  sur quoi le conteneur écoute.
- Une politique réseau qui n'autorise rien n'est pas la même chose qu'aucune
  politique. Dès qu'une politique sélectionne un Pod, tout ce qu'elle ne
  nomme pas est interdit, y compris ce qui marchait avant.
- `kubectl explain` fonctionne sans accès réseau et connaît tout le schéma.
  C'est plus rapide que de chercher un exemple.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, jamais les commandes tapées. Ils entrent
dans le conteneur pour vérifier ce qu'il reçoit vraiment, et le dernier est le
seul qui prouve l'isolation : il ouvre une connexion depuis `frontend`, qui
doit aboutir, et depuis `intrus`, qui ne doit pas aboutir.

```bash
dsoxlab check  ckad-capstone-boutique
dsoxlab submit ckad-capstone-boutique
```
