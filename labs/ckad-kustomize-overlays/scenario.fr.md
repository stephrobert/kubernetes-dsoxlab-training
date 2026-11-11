# Une base Kustomize et deux overlays, dev et prod

## La situation

L'équipe déploie la même application dans deux namespaces, **`dev`** et
**`prod`**, et en a assez de maintenir deux jeux de manifestes qui divergent.
Elle veut une **base** unique, et deux **overlays** qui ne portent que les
différences. Les deux namespaces existent, vides, et le répertoire
**`~/kustomize/`** vous attend, vide lui aussi.

L'application :

- un Deployment **`app`**, conteneur **`web`** sur le port **80**, en version 1 :

  ```text
  version 1 : nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
  version 2 : nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
  ```

- un Service **`app-svc`** sur le port 80, qui le dessert ;
- une configuration **`app-config`**, qui donne au conteneur la variable
  **`MESSAGE=Bienvenue`**, générée par Kustomize et lue par `envFrom`.

## Ce que vous devez obtenir

1. La base vit dans **`~/kustomize/base/`**, les overlays dans
   **`~/kustomize/overlays/dev/`** et **`~/kustomize/overlays/prod/`**, et les
   deux overlays dérivent de cette **même base**.
2. Dans `dev` : **`dev-app`** à **1** réplica disponible ; dans `prod` :
   **`prod-app`** à **3** réplicas disponibles.
3. Les Pods de chaque environnement portent le label **`env=dev`** ou
   **`env=prod`**, et chaque Service, **`dev-app-svc`** et **`prod-app-svc`**,
   trouve les Pods de son environnement.
4. Les deux environnements ont le même conteneur et le même port.
5. **Seul `dev` passe en version 2**, par son overlay : la base décrit toujours
   la version 1, et `prod` y reste.
6. Chaque conteneur lit sa configuration dans une **ConfigMap générée**, dont
   le nom porte l'empreinte de son contenu.
7. Le cluster **correspond au dossier** : comparer chaque overlay au cluster ne
   trouve aucune différence.

## Les repères utiles

Un overlay référence la base dans `resources`, puis ne porte que les
différences : namespace, préfixe des noms, labels, nombre de réplicas, image.
Le label ajouté doit aussi entrer dans le selector du Service, sinon le Service
ne trouve plus ses Pods : Kustomize le fait, si on le lui demande.

Une ConfigMap générée change de nom quand son contenu change, ce qui redémarre
les Pods qui la lisent. Ne modifiez jamais la base pour un seul environnement.

Prévisualisez un overlay avant de l'appliquer, puis comparez-le au cluster.

## Comment vous saurez que c'est bon

Les tests lisent les Deployments, leurs Pods, les Services et leurs endpoints,
les ConfigMaps, puis comparent votre dossier `~/kustomize/` au cluster.

```bash
dsoxlab check ckad-kustomize-overlays
```
