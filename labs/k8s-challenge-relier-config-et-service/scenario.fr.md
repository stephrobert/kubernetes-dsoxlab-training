# Relier un ConfigMap, un Secret et un Service à un Deployment

## La situation

La boutique tourne sur le cluster kind **`boutique`**, et votre `kubectl` le
vise déjà. Sa vitrine doit être livrée dans un namespace à elle, **`magasin`**,
qui n'existe pas encore. Rien n'est en place : vous créez tout.

Les deux images de la vitrine, version actuelle puis version suivante :

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## Ce que vous devez obtenir

1. Tous les objets de la vitrine sont dans le namespace **`magasin`** :
   le Deployment **`vitrine`**, le Service **`vitrine`**, le ConfigMap
   **`vitrine-config`** et le Secret **`vitrine-secret`**. Aucun n'est créé
   dans `default`.

2. Le Deployment **`vitrine`** a **trois réplicas disponibles**.

3. La variable **`MESSAGE_ACCUEIL`**, qui vaut `Bienvenue` dans le conteneur,
   vient du ConfigMap `vitrine-config`.

4. La variable **`DB_PASSWORD`**, qui vaut `Boutique-2026` dans le conteneur,
   vient du Secret `vitrine-secret`, et le mot de passe n'apparaît **jamais en
   clair** dans le Deployment.

5. Le Service **`vitrine`** compte **trois endpoints prêts** et répond en HTTP
   sur `http://vitrine.magasin` depuis un Pod du cluster.

6. La vitrine est passée sur la **version suivante** : ses trois réplicas sont
   disponibles sur la nouvelle image, et l'**ancien ReplicaSet est gardé à
   zéro** réplica.

## Comment vous serez noté

Le challenge est noté sur l'**état du cluster**, jamais sur les commandes
tapées : la configuration et le mot de passe sont lus depuis l'intérieur d'un
Pod. Le seuil est de 70 sur 100. Aucune consigne pas à pas : les leçons du
module ont tout enseigné.

```bash
dsoxlab check  k8s-challenge-relier-config-et-service
dsoxlab submit k8s-challenge-relier-config-et-service
```
