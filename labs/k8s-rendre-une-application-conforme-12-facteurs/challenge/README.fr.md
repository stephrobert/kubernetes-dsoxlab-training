# Challenge : Rendre une application conforme au 12-factor sur Kubernetes

## La situation

L'équipe a livré l'application **`podinfo`** dans le namespace **`douze`**.
Elle tourne, mais elle trahit plusieurs des douze facteurs :

- sa **configuration** est en dur dans les arguments du conteneur ;
- elle écrit son **état** sur un volume `emptyDir` du Pod ;
- rien ne protège les requêtes en cours quand un Pod **s'arrête**.

Un **Redis** tourne à côté, dans le même namespace, joignable par le Service
`redis` sur le port 6379. L'application ne s'en sert pas encore.

Les manifestes de l'application vous attendent dans **`~/douze`**
(`deployment.yaml`, `service.yaml`). Vous êtes sur le control plane, avec
`kubectl` configuré.

## Ce que vous devez obtenir

1. La configuration de podinfo vient d'un **ConfigMap généré par un
   `configMapGenerator` de Kustomize**, dont le nom finit par un hash du
   contenu, injecté par `envFrom`. Plus rien en dur dans les arguments.
2. L'**état vit dans Redis** : le Pod ne porte plus de volume d'état local, et
   une valeur écrite dans le cache de podinfo survit à la suppression du Pod.
3. Le conteneur podinfo a un crochet **`preStop`**.
4. Un **Job `admin-seed`**, avec la même image que l'application, a écrit la
   valeur **`graine-par-le-job`** sous la clé **`seed`** du cache, et il est
   terminé (Complete).

## Les repères

podinfo lit sa configuration dans des variables d'environnement préfixées par
`PODINFO_`. L'adresse de son cache se donne par `PODINFO_CACHE_SERVER`, au
format `tcp://<service>:<port>`. Son API écrit dans le cache par
`POST /cache/<clé>` et relit par `GET /cache/<clé>`.

Un `configMapGenerator` suffixe le nom du ConfigMap d'un hash de son contenu :
changer une valeur crée un nouveau ConfigMap, donc une nouvelle révision du
Deployment. `kubectl apply -k <dossier>` applique une kustomization.

Un Job est immuable : il n'appartient pas à la kustomization de l'application.

## Comment vous saurez que ça marche

Les tests lisent le Deployment, ses volumes et son ConfigMap, écrivent une
valeur dans le cache, suppriment le Pod et la relisent, puis lisent le Job et
la graine.

```bash
dsoxlab check k8s-rendre-une-application-conforme-12-facteurs
```
