# Challenge : Écrire et valider un manifeste

## 📍 La situation

Le cluster kind **`lab`** tourne sur la machine, et votre kubectl le vise déjà.
L'équipe des commandes vous confie son application **`api`**. Un collègue en a
écrit le manifeste, **`~/commandes/api.yaml`** : un seul fichier, avec une
ConfigMap **`api-config`**, un Deployment **`api`** et un Service **`api`**.
Il n'a jamais réussi à l'appliquer en entier.

Dans le namespace **`commandes`**, une **ancienne version** du Deployment
`api` tourne : un réplica, une ancienne image, sans configuration.

L'image de l'application :

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

## 🎯 Ce que vous devez obtenir

1. **`~/commandes/api.yaml`** contient toujours les trois objets dans un seul
   fichier, et le **serveur** l'accepte tel quel.
2. Chacun des trois objets **écrit le namespace `commandes` dans le fichier
   lui-même**. Rien de l'application ne doit se trouver dans `default`.
3. **`api`** a **2 réplicas disponibles**, avec un conteneur sur le port
   **80**, sur l'image ci-dessus.
4. Le Service **`api`**, sur le port **80**, trouve les deux Pods.
5. Le conteneur reçoit **`DEVISE=EUR`** de la ConfigMap **`api-config`**, par
   `envFrom`.
6. Le Deployment `api` qui tourne est **mis à jour en place** : un `api`
   supprimé puis recréé ne compte pas.

## 🧭 Les repères utiles

Le fichier a plusieurs fautes. Certaines se voient à la lecture, une seule est
signalée par le serveur, et une autre ne produit aucune erreur : relisez ce que
le cluster a créé, pas seulement ce que kubectl affiche.

Un objet qui ne nomme pas son namespace va dans celui du contexte courant. Un
Service trouve ses Pods par leurs labels.

Appliquer un manifeste met à jour les objets qui existent déjà, sans les
recréer.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre fichier, le font valider par le serveur, puis lisent
dans le cluster ce qu'il a créé, et l'état du Deployment `api`.

```bash
dsoxlab check k8s-ecrire-un-manifeste
```
