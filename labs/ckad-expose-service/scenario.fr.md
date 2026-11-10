# Exposer un Deployment par un Service ClusterIP

## La situation

Dans le namespace **`lab`**, l'équipe veut un serveur web en **trois
replicas**, joignable par les autres applications du cluster sous un nom
stable, **`web-svc`**, quel que soit le Pod qui répond. Pour vérifier la
répartition, chaque Pod doit répondre avec **son propre nom**.

Un Pod **`client`** est là pour interroger le Service. C'est l'instrument de
mesure du lab, pas une partie du travail : le laisser en place. Si vous le
supprimez, `dsoxlab reset ckad-expose-service` le remet.

## Ce que vous devez obtenir

1. Un Deployment **`web`** dans `lab`, **trois replicas**, image
   **`busybox:1.36`** (les tests lisent l'image des Pods en cours
   d'exécution), dont chaque Pod sert **son propre nom d'hôte** en HTTP sur le
   port **8080**. Ses Pods portent le label **`app=web`**.

   Les trois replicas doivent être **disponibles** : un conteneur dont la
   commande se termine aussitôt redémarre en boucle et ne devient jamais
   disponible.

2. Un Service **`web-svc`** de type **ClusterIP**, port **80**, qui vise le
   port **8080** des Pods `app=web`. Le port cible peut s'écrire avec le
   numéro `8080` ou avec le **nom d'un `containerPort` qui vaut 8080** : les
   deux écritures sont acceptées.

3. Le Service doit avoir **exactement trois endpoints prêts**. Aucun autre Pod
   du namespace ne doit porter le label `app=web` : un Pod resté d'une
   tentative précédente entre lui aussi dans le Service, et fait apparaître un
   quatrième endpoint.

4. Depuis `client`, `http://web-svc/` répond à **dix requêtes sur dix**, chaque
   réponse est le nom d'un **Pod qui existe réellement**, et sur ces dix
   requêtes **au moins deux Pods différents** répondent.

   Chaque Pod est aussi interrogé sur son propre `127.0.0.1:8080` et doit
   répondre **son propre nom** : servir un identifiant inventé, même s'il
   ressemble à un nom de Pod, est refusé.

## Les repères utiles

Un serveur qui répond son nom d'hôte tient en une commande busybox : écrire
`hostname` dans un fichier d'un répertoire, puis servir ce répertoire avec
`httpd` au premier plan. Les options qui comptent sont **`-f`** (rester au
premier plan, sinon le conteneur s'arrête), **`-p 8080`** (le port que
l'exercice demande, `httpd` écoutant sur 80 par défaut) et **`-h
<répertoire>`** (le répertoire à servir). Dans un Pod, le nom d'hôte est le
nom du Pod.

`kubectl expose deployment` crée le Service en une commande, si on lui dit le
port et le port cible.

## Comment vous saurez que c'est bon

Onze critères, un par état demandé ci-dessus : le Deployment et ses Pods, le
Service et ses endpoints, puis dix requêtes depuis `client` et une requête
directe à chaque Pod.

```bash
dsoxlab check ckad-expose-service
```
