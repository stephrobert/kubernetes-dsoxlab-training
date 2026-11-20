# Explore the API with api-resources and explain

The cluster knows better than any web page which types of objects it serves,
and how each one is written. `kubectl api-resources` gives the list of types,
and `kubectl explain` describes their fields. The lesson shows the method on a
simple type. This course takes it further: what the verbs column says, a type
served in two versions that do not say the same thing, the values the cluster
refuses, a probe added to a Deployment that is already running and that
blocks it, and an inventory that loses no type on the way.

You work in a scratch namespace, `essai-api`, with a scratch `Recette` type
and a `menu` application. The challenge will ask you for the same work on
other objects: you will do it on your own, at the end.

Related page: [kubectl api-resources and explain](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-api-resources-explain/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-explorer-l-api
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab`
is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: what you can do with a type

`-o wide` adds the `VERBS` column to `api-resources`: the operations the
cluster accepts on each type. Compare two types:

```bash
kubectl api-resources -o wide | grep -E '^NAME|^tokenreviews |^configmaps '
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND                               VERBS                                                        CATEGORIES
configmaps                          cm           v1                                true         ConfigMap                          create,delete,deletecollection,get,list,patch,update,watch
tokenreviews                                     authentication.k8s.io/v1          false        TokenReview                        create
```

A ConfigMap can be created, read, listed, changed. A `TokenReview` can only be
created: it is a question asked to the cluster ("is this token valid?"), not an
object it keeps. Listing it therefore fails:

```bash
kubectl get tokenreviews
```

```text
Error from server (MethodNotAllowed): the server does not allow this method on the requested resource
```

That is why an inventory only keeps the types that have the `list` verb: the
`--verbs=list` option of exercise 5.

## 📚 Exercise 2: a type served in two versions

A type added by a **CustomResourceDefinition** (CRD) can be served in several
versions at once, while everybody moves to the new one. Create the scratch
`Recette` type, served in `v1beta1` and in `v1`:

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

The `sleep 5` gives the cluster time to publish the schema of the new type.
Now forget that you wrote it, and look at what the cluster says about it:

```bash
kubectl api-resources --api-group=cuisine.exemple.fr
```

```text
NAME       SHORTNAMES   APIVERSION              NAMESPACED   KIND
recettes   rec          cuisine.exemple.fr/v1   true         Recette
```

A single line, in `v1`: `api-resources` shows the version the cluster serves
by default, not all of them. `explain` also describes this version, unless
you ask it for another one with `--api-version`:

```bash
kubectl explain recette.spec
kubectl explain recette.spec --api-version=cuisine.exemple.fr/v1beta1
```

```text title="Excerpt of the output"
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

The two versions do not have the same fields. In `v1`, `plat` and `portions`
are required (`-required-`), and the `enum:` line gives the only values
allowed for `difficulte`. In `v1beta1`, only `plat` exists. Create the scratch
namespace, then a recipe in `v1beta1` that also gives `portions`:

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

Refused: `portions` does not exist in `v1beta1`. The version written in
`apiVersion` decides which fields you are allowed to write. The name of the
group is therefore never enough: read the version in `api-resources`.

## 📚 Exercise 3: the values the cluster refuses

Move the recipe to `v1`, with two wrong values: 20 portions, and a `simple`
difficulty, missing from the list:

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

The cluster checks the object against the schema and names each mistake: the
value outside the list, with the allowed values, and the value outside the
bounds, with the bound. `explain` shows the list (`enum:`). The bounds, for
their part, can only be read in the description, when the author of the type
wrote them there. Fix both values:

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

## 📚 Exercise 4: a probe added to a running Deployment

Create the `menu` application: two agnhost Pods, a small test server that
listens on port 8080 and also answers on `/healthz`. It has no probe:

```bash
kubectl create deployment menu --replicas=2 --image=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6 --port=8080 -n essai-api -- /agnhost netexec --http-port=8080
kubectl rollout status deployment/menu -n essai-api --timeout=120s | tail -1
```

```text
deployment.apps/menu created
deployment "menu" successfully rolled out
```

You have no file for this Deployment. To add a probe to it, you need two
pieces of information: the name of the container, and the fields of the
probe. The name is read in the Deployment, the fields in `explain` (`grep`
only keeps the list of fields):

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

The container is called `agnhost`, and only `port` is required in `httpGet`.
`kubectl patch` changes the Deployment in place: the container is named by its
name, and only the given fields change. First set a probe **on the wrong
port**, 8081, and follow the rollout for 30 seconds:

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

The new Pod runs, but stays at `0/1`: it is never ready. The Deployment waits
for it to be ready before replacing the old ones, which keep serving: the
application does not go down, but the update is stuck. The `Warning` events
say why:

```bash
kubectl get events -n essai-api --field-selector type=Warning -o custom-columns=RAISON:.reason,MESSAGE:.message
```

```text
RAISON      MESSAGE
Unhealthy   Readiness probe failed: Get "http://10.244.0.52:8081/healthz": dial tcp 10.244.0.52:8081: connect: connection refused
```

`connection refused` on port 8081: nothing listens there. Fix the port:

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

Both new Pods are ready, and the last old one goes away. The Pod stuck at
`0/1` was removed without ever serving.

## 📚 Exercise 5: the full inventory of a namespace

Add a Service and a ConfigMap, wait for the old Pod to be gone, then ask for
"everything":

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

Neither the ConfigMap nor the `soupe` recipe. For a real inventory, you query
each type that can be listed and lives in a namespace, leaving out `events`
(too many) and `endpoints` (deprecated since Kubernetes 1.33, it prints a
warning). `cut` and `sort -u` only keep the type of each object. First write
the filter without care:

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

One type is missing. `^(events|endpoints)` leaves out any name that **starts**
with `endpoints`, so `endpointslices.discovery.k8s.io` as well. Yet the `menu`
Service has its EndpointSlices. Anchor the end of the pattern: the name must
stop there, or continue with a dot (`events.events.k8s.io`):

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

This time, nothing is missing. A filter that removes too much says nothing
about it: always check what it leaves out.

## 🧹 Clean up

Delete the scratch namespace, the CRD and the work files:

```bash
kubectl delete namespace essai-api; kubectl delete crd recettes.cuisine.exemple.fr; rm -f ~/crd-recette.yaml ~/soupe.yaml
```

```text
namespace "essai-api" deleted
customresourcedefinition.apiextensions.k8s.io "recettes.cuisine.exemple.fr" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-explorer-l-api
dsoxlab check k8s-explorer-l-api
```

```text
╭─── Result: k8s-explorer-l-api ────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: discover an export type set up by the lab,
served in two versions, create an export with the right fields, add a probe to
a Deployment, and take the inventory of a namespace.

```bash
dsoxlab run k8s-explorer-l-api
dsoxlab challenge k8s-explorer-l-api
```
