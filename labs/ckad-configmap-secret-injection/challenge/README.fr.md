# Challenge : Injecter configuration et secrets dans un Pod

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. L'équipe livre l'application **`app`** dans le namespace **`lab`**.
Elle lit sa configuration de deux façons :

- des **variables d'environnement**, pour ses réglages simples ;
- un fichier **`config.yaml`**, qu'elle attend dans `/etc/app-config`.

Elle a aussi besoin des identifiants de sa base de données. La règle de la
maison est stricte : **aucun mot de passe dans un manifeste de Pod**.

Le namespace existe. Tout le reste est à faire.

## 🎯 Ce que vous devez obtenir

1. Un ConfigMap **`app-settings`** dans `lab`, avec `APP_MODE` à
   `production`, `LOG_LEVEL` à `info`, et une clé **`config.yaml`** dont le
   contenu comporte la ligne `port: 8080`.

2. Un Secret **`db-credentials`** dans `lab`, avec les clés **`DB_HOST`**, à
   `db.internal.svc`, et **`DB_PASSWORD`**, dont vous choisissez la valeur.

3. Un Pod **`app`** dans `lab`, image `nginx:1.30.6`, qui :
   - reçoit **toutes** les clés de `app-settings` en variables d'environnement ;
   - reçoit `DB_HOST` et `DB_PASSWORD` depuis le Secret ;
   - monte `app-settings` dans **`/etc/app-config`**.

4. Depuis l'intérieur du conteneur : `APP_MODE` vaut `production`,
   `DB_PASSWORD` est défini, et `/etc/app-config/config.yaml` contient
   `port: 8080`.

## 🧭 Les repères utiles

Un ConfigMap s'injecte en variables de deux façons : clé par clé, ou d'un bloc.
Un Secret aussi. Le Pod ne porte alors qu'une **référence**, jamais la valeur.

Monté comme un volume, un ConfigMap devient un dossier, où chaque clé est un
fichier. Contrairement aux variables d'environnement, un fichier monté suit
les modifications du ConfigMap, avec un délai.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le ConfigMap, le Secret et la définition du Pod. Ils entrent
ensuite dans le conteneur pour lire les variables et le fichier.

```bash
dsoxlab check ckad-configmap-secret-injection
```
