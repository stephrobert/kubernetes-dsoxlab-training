# Explorer l'API avec api-resources et explain

Un cluster Kubernetes connaît des dizaines de types d'objets, et on peut lui en
ajouter. Personne ne les retient tous : on demande au cluster lui-même.
`kubectl api-resources` liste les types qu'il connaît, et `kubectl explain`
décrit leurs champs. Dans ce cours, vous listez et filtrez les types, vous
lisez la description d'un champ, puis d'une branche entière, vous découvrez un
type que vous n'avez jamais vu, vous voyez ce qu'un objet ne peut pas omettre,
et vous dressez l'inventaire complet d'un namespace.

Vous travaillez avec un type d'essai, `Recette`, que vous créez vous-même, et
un namespace d'essai, `essai-api`. Le challenge vous demandera de découvrir un
autre type, posé par le lab : vous le ferez seul, à la fin.

Page associée : [kubectl api-resources et explain](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-api-resources-explain/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-explorer-l-api
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes 1.37.

## 📚 Exercice 1 : la liste des types

`kubectl api-resources` affiche une ligne par type d'objet. Regardez les
premières lignes :

```bash
kubectl api-resources | head -6
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND
bindings                                         v1                                true         Binding
componentstatuses                   cs           v1                                false        ComponentStatus
configmaps                          cm           v1                                true         ConfigMap
endpoints                           ep           v1                                true         Endpoints
events                              ev           v1                                true         Event
```

Chaque colonne a un usage :

- `NAME` est le nom à taper après `kubectl get` ;
- `SHORTNAMES` donne les raccourcis (`cm` pour `configmaps`) ;
- `APIVERSION` est ce qu'on écrit dans le champ `apiVersion` d'un manifeste ;
- `NAMESPACED` dit si l'objet vit dans un namespace (`true`) ou dans tout le
  cluster (`false`) ;
- `KIND` est ce qu'on écrit dans le champ `kind` d'un manifeste.

Cherchez trois types que vous connaissez déjà :

```bash
kubectl api-resources | grep -E '^(NAME|deployments|pods|services) '
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND
pods                                po           v1                                true         Pod
services                            svc          v1                                true         Service
deployments                         deploy       apps/v1                           true         Deployment
```

Un Pod s'écrit `apiVersion: v1`, mais un Deployment s'écrit `apiVersion:
apps/v1` : `apps` est le **groupe**, `v1` la **version**. Comptez enfin les
types connus de ce cluster :

```bash
kubectl api-resources --no-headers | wc -l
```

```text
71
```

## 📚 Exercice 2 : filtrer par groupe, ou par portée

`--api-group` ne garde que les types d'un groupe :

```bash
kubectl api-resources --api-group=apps
```

```text
NAME                  SHORTNAMES   APIVERSION   NAMESPACED   KIND
controllerrevisions                apps/v1      true         ControllerRevision
daemonsets            ds           apps/v1      true         DaemonSet
deployments           deploy       apps/v1      true         Deployment
replicasets           rs           apps/v1      true         ReplicaSet
statefulsets          sts          apps/v1      true         StatefulSet
```

`--namespaced=false` ne garde que les types qui vivent dans tout le cluster,
hors de tout namespace. Ici, trois d'entre eux :

```bash
kubectl api-resources --namespaced=false | grep -E '^(NAME|namespaces|nodes|persistentvolumes) '
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND
namespaces                          ns           v1                                false        Namespace
nodes                               no           v1                                false        Node
persistentvolumes                   pv           v1                                false        PersistentVolume
```

Un namespace ne se range pas dans un namespace, et un nœud appartient à tout le
cluster : c'est logique.

## 📚 Exercice 3 : expliquer un champ

`kubectl explain` décrit un type, ou un de ses champs. On désigne le champ par
son chemin, avec des points. Voici les champs de `spec` dans un Deployment.
`grep` ne garde que les titres et le nom des champs, pour que la liste tienne à
l'écran :

```bash
kubectl explain deployment.spec | grep -E '^(GROUP|KIND|VERSION|FIELD|DESCRIPTION|FIELDS):|^  [a-zA-Z]+\s|-required-' | head -20
```

```text
GROUP:      apps
KIND:       Deployment
VERSION:    v1
FIELD: spec <DeploymentSpec>
DESCRIPTION:
FIELDS:
  minReadySeconds	<integer>
  paused	<boolean>
  progressDeadlineSeconds	<integer>
  replicas	<integer>
  revisionHistoryLimit	<integer>
  selector	<LabelSelector> -required-
  strategy	<DeploymentStrategy>
  template	<PodTemplateSpec> -required-
```

Chaque champ porte son type entre `< >` : `<integer>` pour un nombre entier,
`<boolean>` pour vrai ou faux. La mention `-required-` signale un champ
**obligatoire** : un Deployment sans `selector` ni `template` est refusé.

Descendez maintenant jusqu'à un champ précis : l'intervalle entre deux essais
d'une sonde de disponibilité, dans le conteneur du Pod. Cette fois, sans
`grep`, la sortie complète :

```bash
kubectl explain deployment.spec.template.spec.containers.readinessProbe.periodSeconds
```

```text
GROUP:      apps
KIND:       Deployment
VERSION:    v1

FIELD: periodSeconds <integer>


DESCRIPTION:
    How often (in seconds) to perform the probe. Default to 10 seconds. Minimum
    value is 1.
```

La description donne l'unité (des secondes), la valeur par défaut (10) et le
minimum (1). C'est ce que vous cherchez quand vous ne savez pas quoi écrire.

## 📚 Exercice 4 : toute une branche d'un coup

`--recursive` affiche tous les champs sous un chemin, avec leurs sous-champs
décalés vers la droite. Voici comment une sonde fait une requête HTTP :

```bash
kubectl explain deployment.spec.template.spec.containers.readinessProbe.httpGet --recursive
```

```text
GROUP:      apps
KIND:       Deployment
VERSION:    v1

FIELD: httpGet <HTTPGetAction>


DESCRIPTION:
    HTTPGet specifies an HTTP GET request to perform.
    HTTPGetAction describes an action based on HTTP Get requests.

FIELDS:
  host	<string>
  httpHeaders	<[]HTTPHeader>
    name	<string> -required-
    value	<string> -required-
  path	<string>
  port	<IntOrString> -required-
  protocol	<string>
  enum: HTTP1, HTTP2
  scheme	<string>
  enum: HTTP, HTTPS
```

D'un coup d'œil : `port` est obligatoire, `path` ne l'est pas. `<[]HTTPHeader>`
veut dire une **liste** d'en-têtes. `enum:` donne les seules valeurs
acceptées. Pour écrire une sonde HTTP, il suffit donc de `httpGet`, avec au
moins un `port`.

## 📚 Exercice 5 : un type que personne ne vous a présenté

On peut ajouter un type au cluster avec une **CustomResourceDefinition**
(CRD). Créez le type d'essai `Recette`, dans le groupe `cuisine.exemple.fr` :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: recettes.cuisine.exemple.fr
spec:
  group: cuisine.exemple.fr
  scope: Namespaced
  names:
    plural: recettes
    singular: recette
    kind: Recette
    shortNames: [rec]
  versions:
    - name: v1beta1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              description: Ce que la recette demande.
              required: [plat, portions]
              properties:
                plat:
                  type: string
                  description: Le nom du plat.
                portions:
                  type: integer
                  description: Le nombre de personnes, de 1 a 12.
                  minimum: 1
                  maximum: 12
YAML
```

```text
customresourcedefinition.apiextensions.k8s.io/recettes.cuisine.exemple.fr created
```

Le cluster met quelques secondes à publier un nouveau type. Attendez qu'il soit
prêt :

```bash
kubectl wait --for=condition=Established crd/recettes.cuisine.exemple.fr --timeout=60s; sleep 5
```

```text
customresourcedefinition.apiextensions.k8s.io/recettes.cuisine.exemple.fr condition met
```

Oubliez maintenant que vous l'avez écrit, et faites comme devant un type
inconnu. D'abord, sa ligne dans `api-resources` :

```bash
kubectl api-resources --api-group=cuisine.exemple.fr
```

```text
NAME       SHORTNAMES   APIVERSION                   NAMESPACED   KIND
recettes   rec          cuisine.exemple.fr/v1beta1   true         Recette
```

Un manifeste de ce type commence donc par `apiVersion:
cuisine.exemple.fr/v1beta1` et `kind: Recette`. Le nom du groupe ne disait pas
la version : c'est cette colonne qui la donne. Ensuite, ses champs :

```bash
kubectl explain recette.spec
```

```text
GROUP:      cuisine.exemple.fr
KIND:       Recette
VERSION:    v1beta1

FIELD: spec <Object>


DESCRIPTION:
    Ce que la recette demande.

FIELDS:
  plat	<string> -required-
    Le nom du plat.

  portions	<integer> -required-
    Le nombre de personnes, de 1 a 12.
```

`explain` lit la description écrite par l'auteur du type. Les deux champs sont
obligatoires, et la description de `portions` dit son format.

## 📚 Exercice 6 : ce qu'un objet ne peut pas omettre

Créez le namespace d'essai, puis une recette **sans** `portions` :

```bash
kubectl create namespace essai-api
cat <<'YAML' | kubectl apply -n essai-api -f -
apiVersion: cuisine.exemple.fr/v1beta1
kind: Recette
metadata:
  name: soupe
spec:
  plat: soupe au potiron
YAML
```

```text
namespace/essai-api created
The Recette "soupe" is invalid: spec.portions: Required value
```

Le cluster refuse l'objet et nomme le champ manquant : c'est le `-required-`
vu dans `explain`. Ajoutez-le :

```bash
cat <<'YAML' | kubectl apply -n essai-api -f -
apiVersion: cuisine.exemple.fr/v1beta1
kind: Recette
metadata:
  name: soupe
spec:
  plat: soupe au potiron
  portions: 4
YAML
kubectl get rec -n essai-api
```

```text
recette.cuisine.exemple.fr/soupe created
NAME    AGE
soupe   0s
```

Le raccourci `rec`, lu dans la colonne `SHORTNAMES`, fonctionne comme pour
`cm` ou `deploy`.

## 📚 Exercice 7 : l'inventaire complet d'un namespace

Ajoutez une ConfigMap dans le namespace, puis demandez « tout » :

```bash
kubectl create configmap reglages --from-literal=a=1 -n essai-api
kubectl get all -n essai-api
```

```text
configmap/reglages created
No resources found in essai-api namespace.
```

« Aucune ressource », alors que le namespace contient une recette et une
ConfigMap. `kubectl get all` ne regarde qu'une petite liste de types (Pods,
Services, Deployments et quelques autres). Il ne voit ni les ConfigMaps, ni
les types ajoutés par une CRD.

Pour un vrai inventaire, demandez à `api-resources` les types **listables**
(`--verbs=list`) **et rangés dans un namespace** (`--namespaced`), avec leur
seul nom (`-o name`). Puis interrogez-les un par un avec `xargs`. Les
événements (`events`) sont écartés car ils sont trop nombreux. `endpoints`
l'est aussi : ce type est déprécié depuis Kubernetes 1.33 au profit des
EndpointSlices, et le lire affiche un avertissement :

```bash
kubectl api-resources --verbs=list --namespaced -o name | grep -v -E '^(events|endpoints)' | xargs -n1 kubectl get -n essai-api --ignore-not-found -o name
```

```text
configmap/kube-root-ca.crt
configmap/reglages
serviceaccount/default
recette.cuisine.exemple.fr/soupe
```

Cette fois, tout y est. `kube-root-ca.crt` et le compte `default` sont créés
automatiquement dans chaque namespace. `--ignore-not-found` évite un message
pour chaque type absent du namespace.

## 🧹 Nettoyage

Supprimez le namespace d'essai, puis le type `Recette` :

```bash
kubectl delete namespace essai-api; kubectl delete crd recettes.cuisine.exemple.fr
```

```text
namespace "essai-api" deleted
customresourcedefinition.apiextensions.k8s.io "recettes.cuisine.exemple.fr" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-explorer-l-api
dsoxlab check k8s-explorer-l-api
```

```text
╭── Résultat : k8s-explorer-l-api ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : découvrir un type de sauvegarde posé par le lab,
créer une sauvegarde avec les bons champs, ajouter une sonde à un Deployment,
et dresser l'inventaire d'un namespace.

```bash
dsoxlab run k8s-explorer-l-api
dsoxlab challenge k8s-explorer-l-api
```
