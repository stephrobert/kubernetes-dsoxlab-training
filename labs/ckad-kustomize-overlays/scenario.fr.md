# Une base Kustomize et deux overlays, dev et prod

## La situation

L'équipe déploie la même application dans deux namespaces, **`dev`** et
**`prod`**, et en a assez de maintenir deux jeux de manifestes qui
divergent. Elle veut une **base** unique, et deux **overlays** qui ne
portent que les différences. Les deux namespaces existent.

L'application, c'est un Deployment **`app`**, image `nginx:1.27-alpine`, et
un Service **`app-svc`** sur le port 80 qui le dessert.

## Ce que vous devez obtenir

1. Dans `dev` : un Deployment **`dev-app`** à **1** replica, dont les Pods
   portent le label `env=dev`, et un Service **`dev-app-svc`** qui a des
   endpoints.

2. Dans `prod` : un Deployment **`prod-app`** à **3** replicas, dont les Pods
   portent le label `env=prod`, et un Service **`prod-app-svc`** qui a des
   endpoints.

3. Les deux environnements viennent de la **même base** : même image, même
   port, même structure, seuls le namespace, le nombre de replicas, le
   préfixe des noms et le label d'environnement diffèrent.

## Les repères utiles

`kubectl apply -k <répertoire>` applique un `kustomization.yaml`. Un overlay
référence la base dans `resources`, et Kustomize sait préfixer les noms,
fixer un namespace, ajouter des labels jusque dans les selectors, et changer
un nombre de replicas, sans toucher à la base.

Le label ajouté doit aussi entrer dans le selector du Service, sinon le
Service ne trouve plus ses Pods : Kustomize le fait pour vous, si on le lui
demande.

## Comment vous saurez que c'est bon

Les tests lisent les Deployments, leurs Pods, les Services et leurs
endpoints dans les deux namespaces, et comparent la structure des deux
environnements.

```bash
dsoxlab check ckad-kustomize-overlays
```
