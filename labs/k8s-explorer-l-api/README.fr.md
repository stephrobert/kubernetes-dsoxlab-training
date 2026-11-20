# Explorer l'API avec api-resources et explain

Le cluster sait mieux que n'importe quelle page web quels types d'objets il
sert, et comment chacun s'écrit. `kubectl api-resources` donne la liste des
types, et `kubectl explain` décrit leurs champs. La leçon montre la méthode
sur un type simple. Ce cours la pousse plus loin : ce que dit la colonne des
verbes, un type servi en deux versions qui ne disent pas la même chose, les
valeurs que le cluster refuse, une sonde ajoutée à un Deployment qui tourne
déjà et qui le bloque, et un inventaire qui ne perd aucun type en route.

Vous travaillez dans un namespace d'essai, `essai-api`, avec un type d'essai
`Recette` et une application `menu`. Le challenge vous demandera le même
travail sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [kubectl api-resources et explain](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-api-resources-explain/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-explorer-l-api
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026.

## 📚 Exercice 1 : ce qu'on peut faire d'un type

`-o wide` ajoute à `api-resources` la colonne `VERBS` : les opérations que le
cluster accepte sur chaque type. Comparez deux types :

```bash
kubectl api-resources -o wide | grep -E '^NAME|^tokenreviews |^configmaps '
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND                               VERBS                                                        CATEGORIES
configmaps                          cm           v1                                true         ConfigMap                          create,delete,deletecollection,get,list,patch,update,watch
tokenreviews                                     authentication.k8s.io/v1          false        TokenReview                        create
```

Une ConfigMap se crée, se lit, se liste, se modifie. Un `TokenReview` ne fait
que se créer : c'est une question qu'on pose au cluster (« ce jeton est-il
valide ? »), pas un objet qu'il garde. Le lister échoue donc :

```bash
kubectl get tokenreviews
```

```text
Error from server (MethodNotAllowed): the server does not allow this method on the requested resource
```

C'est pourquoi un inventaire ne garde que les types qui ont le verbe `list` :
l'option `--verbs=list` de l'exercice 5.

## 📚 Exercice 2 : un type servi en deux versions

Un type ajouté par une **CustomResourceDefinition** (CRD) peut être servi en
plusieurs versions à la fois, le temps que tout le monde passe à la nouvelle.
Créez le type d'essai `Recette`, servi en `v1beta1` et en `v1` :

```bash
cat > ~/crd-recette.yaml <<'YAML'
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
      storage: false
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                plat:
                  type: string
                  description: Le nom du plat.
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: [plat, portions]
              properties:
                plat:
                  type: string
                  description: Le nom du plat.
                portions:
                  type: integer
                  minimum: 1
                  maximum: 12
                  description: Le nombre de personnes, de 1 a 12.
                difficulte:
                  type: string
                  enum: [facile, moyenne, difficile]
                  description: La difficulte de la recette.
YAML
kubectl apply -f ~/crd-recette.yaml
kubectl wait --for=condition=Established crd/recettes.cuisine.exemple.fr --timeout=60s; sleep 5
```

```text
customresourcedefinition.apiextensions.k8s.io/recettes.cuisine.exemple.fr created
customresourcedefinition.apiextensions.k8s.io/recettes.cuisine.exemple.fr condition met
```

Le `sleep 5` laisse au cluster le temps de publier le schéma du nouveau type.
Oubliez maintenant que vous l'avez écrit, et regardez ce que le cluster en
dit :

```bash
kubectl api-resources --api-group=cuisine.exemple.fr
```

```text
NAME       SHORTNAMES   APIVERSION              NAMESPACED   KIND
recettes   rec          cuisine.exemple.fr/v1   true         Recette
```

Une seule ligne, en `v1` : `api-resources` montre la version que le cluster
sert par défaut, pas toutes. `explain` décrit aussi cette version, sauf si on
lui en demande une autre avec `--api-version` :

```bash
kubectl explain recette.spec
kubectl explain recette.spec --api-version=cuisine.exemple.fr/v1beta1
```

```text title="Extrait de la sortie"
VERSION:    v1
...
FIELDS:
  difficulte	<string>
  enum: facile, moyenne, difficile
    La difficulte de la recette.

  plat	<string> -required-
    Le nom du plat.

  portions	<integer> -required-
    Le nombre de personnes, de 1 a 12.

...
VERSION:    v1beta1
...
FIELDS:
  plat	<string>
    Le nom du plat.
```

Les deux versions n'ont pas les mêmes champs. En `v1`, `plat` et `portions`
sont obligatoires (`-required-`), et la ligne `enum:` donne les seules valeurs
permises pour `difficulte`. En `v1beta1`, seul `plat` existe. Créez le
namespace d'essai, puis une recette en `v1beta1` qui donne aussi `portions` :

```bash
kubectl create namespace essai-api
cat > ~/soupe.yaml <<'YAML'
apiVersion: cuisine.exemple.fr/v1beta1
kind: Recette
metadata:
  name: soupe
spec:
  plat: soupe au potiron
  portions: 4
YAML
kubectl apply -n essai-api -f ~/soupe.yaml
```

```text
namespace/essai-api created
Error from server (BadRequest): error when creating "/home/ansible/soupe.yaml": Recette in version "v1beta1" cannot be handled as a Recette: strict decoding error: unknown field "spec.portions"
```

Refusé : `portions` n'existe pas en `v1beta1`. La version écrite dans
`apiVersion` décide des champs que vous avez le droit d'écrire. Le nom du
groupe ne suffit donc jamais : lisez la version dans `api-resources`.

## 📚 Exercice 3 : les valeurs que le cluster refuse

Passez la recette en `v1`, avec deux valeurs fautives : 20 portions, et une
difficulté `simple`, absente de la liste :

```bash
cat > ~/soupe.yaml <<'YAML'
apiVersion: cuisine.exemple.fr/v1
kind: Recette
metadata:
  name: soupe
spec:
  plat: soupe au potiron
  portions: 20
  difficulte: simple
YAML
kubectl apply -n essai-api -f ~/soupe.yaml
```

```text
The Recette "soupe" is invalid:
* spec.difficulte: Unsupported value: "simple": supported values: "facile", "moyenne", "difficile"
* spec.portions: Invalid value: 20: spec.portions in body should be less than or equal to 12
```

Le cluster vérifie l'objet contre le schéma et nomme chaque faute : la valeur
hors liste, avec les valeurs permises, et la valeur hors bornes, avec la
borne. `explain` affiche la liste (`enum:`). Les bornes, elles, ne se lisent
que dans la description, quand l'auteur du type les y a écrites. Corrigez les
deux valeurs :

```bash
sed -i -e 's/portions: 20/portions: 4/' -e 's/difficulte: simple/difficulte: facile/' ~/soupe.yaml
kubectl apply -n essai-api -f ~/soupe.yaml
kubectl get rec -n essai-api
```

```text
recette.cuisine.exemple.fr/soupe created
NAME    AGE
soupe   0s
```

## 📚 Exercice 4 : une sonde ajoutée à un Deployment qui tourne

Créez l'application `menu` : deux Pods agnhost, un petit serveur de test qui
écoute sur le port 8080 et répond aussi sur `/healthz`. Elle n'a pas de
sonde :

```bash
kubectl create deployment menu --replicas=2 --image=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6 --port=8080 -n essai-api -- /agnhost netexec --http-port=8080
kubectl rollout status deployment/menu -n essai-api --timeout=120s | tail -1
```

```text
deployment.apps/menu created
deployment "menu" successfully rolled out
```

Vous n'avez pas de fichier pour ce Deployment. Pour lui ajouter une sonde, il
faut deux informations : le nom du conteneur, et les champs de la sonde. Le
nom se lit dans le Deployment, les champs dans `explain` (`grep` ne garde que
la liste des champs) :

```bash
kubectl get deployment menu -n essai-api -o jsonpath='{.spec.template.spec.containers[0].name}{" "}{.spec.template.spec.containers[0].ports}{"\n"}'
kubectl explain deployment.spec.template.spec.containers.readinessProbe.httpGet | grep -E '^  [a-z]'
```

```text
agnhost [{"containerPort":8080,"protocol":"TCP"}]
  host	<string>
  httpHeaders	<[]HTTPHeader>
  path	<string>
  port	<IntOrString> -required-
  protocol	<string>
  enum: HTTP1, HTTP2
  scheme	<string>
  enum: HTTP, HTTPS
```

Le conteneur s'appelle `agnhost`, et seul `port` est obligatoire dans
`httpGet`. `kubectl patch` modifie le Deployment en place : le conteneur est
désigné par son nom, et seuls les champs donnés changent. Posez d'abord une
sonde **sur le mauvais port**, 8081, et suivez le déploiement 30 secondes :

```bash
kubectl patch deployment menu -n essai-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"agnhost","readinessProbe":{"httpGet":{"path":"/healthz","port":8081}}}]}}}}'
kubectl rollout status deployment/menu -n essai-api --timeout=30s
kubectl get pods -n essai-api -l app=menu
```

```text
deployment.apps/menu patched
Waiting for deployment "menu" rollout to finish: 1 out of 2 new replicas have been updated...
error: timed out waiting for the condition
NAME                    READY   STATUS    RESTARTS   AGE
menu-5f79c74c9c-hdznl   0/1     Running   0          31s
menu-6cdfbbf4b5-c6dfz   1/1     Running   0          31s
menu-6cdfbbf4b5-mnw2t   1/1     Running   0          31s
```

Le nouveau Pod tourne, mais reste à `0/1` : il n'est jamais prêt. Le
Deployment attend qu'il le soit pour remplacer les anciens, qui continuent de
servir : l'application ne tombe pas, mais la mise à jour est bloquée. Les
événements de type `Warning` disent pourquoi :

```bash
kubectl get events -n essai-api --field-selector type=Warning -o custom-columns=RAISON:.reason,MESSAGE:.message
```

```text
RAISON      MESSAGE
Unhealthy   Readiness probe failed: Get "http://10.244.0.52:8081/healthz": dial tcp 10.244.0.52:8081: connect: connection refused
```

`connection refused` sur le port 8081 : rien n'y écoute. Corrigez le port :

```bash
kubectl patch deployment menu -n essai-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"agnhost","readinessProbe":{"httpGet":{"path":"/healthz","port":8080}}}]}}}}'
kubectl rollout status deployment/menu -n essai-api --timeout=120s | tail -1; kubectl get pods -n essai-api -l app=menu
```

```text
deployment.apps/menu patched
deployment "menu" successfully rolled out
NAME                    READY   STATUS        RESTARTS   AGE
menu-6cdfbbf4b5-c6dfz   1/1     Terminating   0          33s
menu-6d8c8c7744-869n5   1/1     Running       0          1s
menu-6d8c8c7744-pt9xq   1/1     Running       0          2s
```

Les deux nouveaux Pods sont prêts, et le dernier ancien s'en va. Le Pod bloqué
à `0/1` a été retiré sans jamais avoir servi.

## 📚 Exercice 5 : l'inventaire complet d'un namespace

Ajoutez un Service et une ConfigMap, attendez que l'ancien Pod soit parti,
puis demandez « tout » :

```bash
kubectl expose deployment menu --port=80 --target-port=8080 -n essai-api
kubectl create configmap reglages --from-literal=a=1 -n essai-api
sleep 15; kubectl get all -n essai-api
```

```text
service/menu exposed
configmap/reglages created
NAME                        READY   STATUS    RESTARTS   AGE
pod/menu-6d8c8c7744-869n5   1/1     Running   0          16s
pod/menu-6d8c8c7744-pt9xq   1/1     Running   0          17s

NAME           TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
service/menu   ClusterIP   10.96.224.147   <none>        80/TCP    15s

NAME                   READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/menu   2/2     2            2           48s

NAME                              DESIRED   CURRENT   READY   AGE
replicaset.apps/menu-5f79c74c9c   0         0         0       48s
replicaset.apps/menu-6cdfbbf4b5   0         0         0       48s
replicaset.apps/menu-6d8c8c7744   2         2         2       17s
```

Ni la ConfigMap, ni la recette `soupe`. Pour un vrai inventaire, on interroge
chaque type listable et rangé dans un namespace, en écartant `events` (trop
nombreux) et `endpoints` (déprécié depuis Kubernetes 1.33, il affiche un
avertissement). `cut` et `sort -u` ne gardent que le type de chaque objet.
Écrivez d'abord le filtre sans précaution :

```bash
kubectl api-resources --verbs=list --namespaced -o name | grep -v -E '^(events|endpoints)' | xargs -n1 kubectl get -n essai-api --ignore-not-found -o name | cut -d/ -f1 | sort -u
```

```text
configmap
deployment.apps
pod
recette.cuisine.exemple.fr
replicaset.apps
service
serviceaccount
```

Il manque un type. `^(events|endpoints)` écarte tout nom qui **commence** par
`endpoints`, donc aussi `endpointslices.discovery.k8s.io`. Or le Service
`menu` a ses EndpointSlices. Ancrez la fin du motif : le nom doit s'arrêter là,
ou continuer par un point (`events.events.k8s.io`) :

```bash
kubectl api-resources --verbs=list --namespaced -o name | grep -v -E '^(events|endpoints)(\.|$)' | xargs -n1 kubectl get -n essai-api --ignore-not-found -o name | cut -d/ -f1 | sort -u
```

```text
configmap
deployment.apps
endpointslice.discovery.k8s.io
pod
recette.cuisine.exemple.fr
replicaset.apps
service
serviceaccount
```

Cette fois, rien ne manque. Un filtre qui retire trop ne dit rien : vérifiez
toujours ce qu'il écarte.

## 🧹 Nettoyage

Supprimez le namespace d'essai, la CRD et les fichiers de travail :

```bash
kubectl delete namespace essai-api; kubectl delete crd recettes.cuisine.exemple.fr; rm -f ~/crd-recette.yaml ~/soupe.yaml
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

À vous, seul cette fois : découvrir un type d'export posé par le lab, servi
en deux versions, créer un export avec les bons champs, ajouter une sonde à un
Deployment, et dresser l'inventaire d'un namespace.

```bash
dsoxlab run k8s-explorer-l-api
dsoxlab challenge k8s-explorer-l-api
```
