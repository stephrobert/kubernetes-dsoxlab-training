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

3. **Le mot de passe de la base n'est ni écrit dans la définition du
   catalogue, ni posé dans son environnement.** Il vaut `s3cr3t-boutique`, il
   est détenu par un objet dédié nommé `catalogue-db` sous la clé `password`,
   et le conteneur le lit dans le fichier `/etc/db/password`.

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

## Si vous bloquez

Un micro-lab vous donne ses repères gratuitement. Un capstone, non : c'est
justement ce qu'il mesure. Les quatre indices de ce lab vont du plus vague au
plus explicite, ils **coûtent des points**, et ils portent exactement les
pièges que ce capstone attrape.

```bash
dsoxlab hint ckad-capstone-boutique
```

Vous avez donc le choix, comme le jour de l'épreuve : chercher, ou payer pour
être orienté. Les deux sont des réponses légitimes, et votre score les
distingue.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, jamais les commandes tapées. Ils entrent
dans le conteneur pour vérifier ce qu'il reçoit vraiment, et le dernier est le
seul qui prouve l'isolation : il ouvre une connexion depuis `frontend`, qui
doit aboutir, et depuis `intrus`, qui ne doit pas aboutir.

```bash
dsoxlab check  ckad-capstone-boutique
dsoxlab submit ckad-capstone-boutique
```
