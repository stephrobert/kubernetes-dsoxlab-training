# Challenge : Une base Kustomize et deux overlays, recette et production

## 📍 La situation

L'équipe déploie l'application **`catalogue`** dans deux namespaces,
**`recette`** et **`production`**. Elle en a assez de tenir deux jeux de
manifestes qui finissent par diverger. Elle veut une seule **base**, et deux
**overlays** qui ne contiennent que les différences. Les deux namespaces
existent et sont vides. Le répertoire **`~/kustomize/`** vous attend, vide lui
aussi.

L'application :

- un Deployment **`catalogue`**, avec un conteneur **`web`** sur le port
  **80**, en version 1 :

  ```text
  version 1 : nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
  version 2 : nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
  ```

- un Service **`catalogue-svc`** sur le port 80, devant lui ;
- une configuration **`catalogue-config`**, qui donne au conteneur deux
  variables, **`MODE=lecture`** et **`ACCUEIL=Bienvenue`**. Kustomize la
  génère, et le conteneur la lit par `envFrom`.

## 🎯 Ce que vous devez obtenir

1. La base est dans **`~/kustomize/base/`**, les overlays dans
   **`~/kustomize/overlays/recette/`** et
   **`~/kustomize/overlays/production/`**. Les deux overlays partent de cette
   **même base**.
2. Dans `recette` : **`rec-catalogue`** avec **2** réplicas disponibles. Dans
   `production` : **`prd-catalogue`** avec **4** réplicas disponibles.
3. Les Pods de chaque environnement portent le label **`palier=recette`** ou
   **`palier=production`**. Chaque Service, **`rec-catalogue-svc`** et
   **`prd-catalogue-svc`**, trouve les Pods de son environnement.
4. Les deux environnements ont le même conteneur et le même port.
5. **Seule `recette` passe en version 2**, par son overlay. La base décrit
   toujours la version 1, et `production` y reste.
6. Chaque conteneur lit sa configuration dans une **ConfigMap générée**, dont
   le nom porte une empreinte de son contenu. En **production**, `MODE` vaut
   **`ecriture`**, et `ACCUEIL` garde la valeur de la base. En recette, rien ne
   change.
7. Le cluster **correspond au dossier** : comparer chaque overlay au cluster
   ne montre aucune différence.

## 🧭 Les repères utiles

Un overlay cite la base dans `resources`, puis ne contient que les
différences : namespace, préfixe des noms, labels, nombre de réplicas, image.
Le label ajouté doit aussi entrer dans le sélecteur du Service, sinon le
Service ne trouve plus ses Pods : Kustomize le fait, si on le lui demande.

Un générateur de l'overlay peut **remplacer** celui de la base, ou **fusionner**
avec lui : seule la fusion garde les valeurs que l'overlay ne cite pas. Une
ConfigMap générée change de nom quand son contenu change, ce qui redémarre les
Pods qui la lisent. Ne modifiez jamais la base pour un seul environnement.

Regardez ce que produit un overlay avant de l'appliquer, puis comparez-le au
cluster.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les Deployments, leurs Pods, les Services et leurs adresses,
les ConfigMaps, puis comparent votre dossier `~/kustomize/` au cluster.

```bash
dsoxlab check ckad-kustomize-overlays
```
