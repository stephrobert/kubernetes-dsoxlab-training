# Installer un opérateur et configurer ce qu'il fait tourner

## La situation

L'équipe du registre veut une base MongoDB sur le cluster kubeadm du catalogue,
et elle ne veut pas l'exploiter à la main : un **opérateur** s'en chargera.
L'opérateur retenu est **MongoDB Controllers for Kubernetes (MCK) 1.15.0**, dont
la matrice de compatibilité officielle couvre Kubernetes 1.35, 1.36 et 1.37.

Le cluster fournit une StorageClass par défaut, `local-path`. Rien d'autre n'est
installé : ni l'opérateur, ni ses définitions, ni son namespace.

Les deux manifestes de l'opérateur, au tag de la version :

```text
https://raw.githubusercontent.com/mongodb/mongodb-kubernetes/1.15.0/public/crds.yaml
https://raw.githubusercontent.com/mongodb/mongodb-kubernetes/1.15.0/public/mongodb-kubernetes.yaml
```

Les deux images à épingler, avec leur digest :

```text
quay.io/mongodb/mongodb-kubernetes:1.15.0@sha256:953d43a57a5d4ebcb7f726a6d93dead23c75231ca753b68865bf098232cbce1a
quay.io/mongodb/mongodb-community-server:9.0.8-ubi8@sha256:77351e6c8e806a5f55949212e2fe521d0866069d3348d1032414e2e256cd9651
```

## Ce que vous devez obtenir

1. La CRD **`mongodbcommunity.mongodbcommunity.mongodb.com`** est **établie**.

2. Le Deployment **`mongodb-kubernetes-operator`**, dans le namespace
   **`mongodb`**, est **disponible**, et lance l'image de l'opérateur
   **épinglée par son digest**.

3. Une ressource **MongoDBCommunity** nommée **`registre`**, dans `mongodb`, en
   phase **`Running`**. C'est un replica set à **un membre**, en version
   **`9.0.8`**, avec un utilisateur **`atelier`** (base `admin`) dont le mot de
   passe vit dans le Secret **`atelier-mot-de-passe`**, clé `password`.

4. Le StatefulSet **`registre`** et le Service **`registre-svc`** existent, et ils
   **appartiennent à la ressource** `registre` : c'est l'opérateur qui les a créés.

5. Le conteneur **`mongod`** tourne sur l'image du serveur **épinglée par son
   digest**.

6. **En ne modifiant que la ressource**, vous avez fixé le seuil des opérations
   lentes de mongod à **250 ms** (`operationProfiling.slowOpThresholdMs`), et
   mongod a **redémarré avec ce réglage**.

## Les repères utiles

L'ordre compte : le namespace d'abord, puisque le manifeste de l'opérateur le
suppose sans le créer ; les définitions ensuite ; l'opérateur enfin. Une
ressource appliquée avant sa CRD est refusée.

Le manifeste de l'opérateur désigne ses images par **tag**. Remplacez celle de
l'opérateur par sa forme épinglée **avant** de l'appliquer. Le serveur MongoDB,
lui, n'apparaît pas dans ce manifeste : l'opérateur compose son nom à partir de
la version de la ressource. Il s'épingle donc **dans la ressource**, sous
`spec.statefulSet`, sur le conteneur `mongod`.

Les nœuds de ce cluster sont petits. Les demandes par défaut du replica set ne
tiennent pas : réduisez-les sous `spec.statefulSet`, à **100m** de CPU par
conteneur (`mongod` et `mongodb-agent`), comme le fait un des exemples du dépôt
de l'opérateur (`public/samples`).

Le premier passage en `Running` prend plusieurs minutes : l'image du serveur
pèse 433 Mo. Une fois la ressource modifiée, l'opérateur repasse par `Pending`
le temps de redémarrer mongod, puis revient à `Running`.

## Comment vous saurez que c'est bon

Chaque test vérifie un des six états ci-dessus. Le quatrième lit les
propriétaires des objets : un StatefulSet monté à la main porterait les mêmes
noms, sans propriétaire. Le sixième lit les **options de démarrage** de mongod :
un réglage posé à chaud dans mongod ne les change pas, et disparaîtrait au
premier redémarrage.

```bash
dsoxlab check cka-operateur-installer-et-configurer
```
