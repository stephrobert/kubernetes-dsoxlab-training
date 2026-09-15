# Injecter configuration et secrets dans un Pod

## La situation

L'équipe livre l'application **`app`** dans le namespace **`lab`**. Elle lit
sa configuration de deux façons : des **variables d'environnement** pour ses
réglages simples, et un fichier **`config.yaml`** qu'elle attend sous
`/etc/app-config`. Elle a aussi besoin des identifiants de sa base de
données, et la règle de la maison est stricte : **aucun mot de passe dans un
manifeste de Pod**.

Le namespace existe. Tout le reste est à faire.

## Ce que vous devez obtenir

1. Un ConfigMap **`app-settings`** dans `lab`, avec `APP_MODE` valant
   `production`, `LOG_LEVEL` valant `info`, et une clé **`config.yaml`** dont
   le contenu comporte la ligne `port: 8080`.

2. Un Secret **`db-credentials`** dans `lab`, avec les clés **`DB_HOST`**,
   valant `db.internal.svc`, et **`DB_PASSWORD`**, dont vous choisissez la
   valeur.

3. Un Pod **`app`** dans `lab`, image `nginx:1.27-alpine`, qui reçoit
   **toutes** les clés de `app-settings` en variables d'environnement, qui
   reçoit `DB_HOST` et `DB_PASSWORD` depuis le Secret, et qui monte
   `app-settings` sous **`/etc/app-config`**.

4. De l'intérieur du conteneur : `APP_MODE` vaut `production`, `DB_PASSWORD`
   est défini, et `/etc/app-config/config.yaml` contient `port: 8080`.

## Les repères utiles

Il y a deux façons d'injecter un ConfigMap en variables : clé par clé, ou
d'un bloc. Même chose pour un Secret. Le Pod ne porte alors qu'une
**référence**, jamais la valeur.

Monté comme un volume, un ConfigMap devient un répertoire : chaque clé y est
un fichier. Et contrairement aux variables d'environnement, un fichier monté
suit les modifications du ConfigMap, avec un délai.

## Comment vous saurez que c'est bon

Les tests lisent le ConfigMap, le Secret et la définition du Pod, puis ils
entrent dans le conteneur pour lire les variables et le fichier.

```bash
dsoxlab check ckad-configmap-secret-injection
```
