# Explore the API with api-resources and explain

A Kubernetes cluster knows dozens of object types, and you can add more. Nobody
remembers them all: you ask the cluster itself. `kubectl api-resources` lists
the types it knows, and `kubectl explain` describes their fields. In this
course, you list and filter the types, you read the description of a field,
then of a whole branch, you discover a type you have never seen, you see what
an object cannot leave out, and you take the full inventory of a namespace.

You work with a trial type, `Recette` (French for "recipe"), that you create
yourself, and a scratch namespace, `essai-api`. The challenge will ask you to
discover another type, set up by the lab: you will do it on your own, at the
end.

Related page: [kubectl api-resources and explain](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/outils/kubectl-api-resources-explain/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-explorer-l-api
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab` is
running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes 1.37.

## 📚 Exercise 1: the list of types

`kubectl api-resources` shows one line per object type. Look at the first
lines:

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

Each column has a use:

- `NAME` is the name to type after `kubectl get`;
- `SHORTNAMES` gives the shortcuts (`cm` for `configmaps`);
- `APIVERSION` is what you write in the `apiVersion` field of a manifest;
- `NAMESPACED` tells whether the object lives in a namespace (`true`) or in
  the whole cluster (`false`);
- `KIND` is what you write in the `kind` field of a manifest.

Look for three types you already know:

```bash
kubectl api-resources | grep -E '^(NAME|deployments|pods|services) '
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND
pods                                po           v1                                true         Pod
services                            svc          v1                                true         Service
deployments                         deploy       apps/v1                           true         Deployment
```

A Pod is written `apiVersion: v1`, but a Deployment is written `apiVersion:
apps/v1`: `apps` is the **group**, `v1` the **version**. Finally, count the
types this cluster knows:

```bash
kubectl api-resources --no-headers | wc -l
```

```text
71
```

## 📚 Exercise 2: filter by group, or by scope

`--api-group` keeps only the types of one group:

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

`--namespaced=false` keeps only the types that live in the whole cluster,
outside any namespace. Here, three of them:

```bash
kubectl api-resources --namespaced=false | grep -E '^(NAME|namespaces|nodes|persistentvolumes) '
```

```text
NAME                                SHORTNAMES   APIVERSION                        NAMESPACED   KIND
namespaces                          ns           v1                                false        Namespace
nodes                               no           v1                                false        Node
persistentvolumes                   pv           v1                                false        PersistentVolume
```

A namespace is not stored in a namespace, and a node belongs to the whole
cluster: that makes sense.

## 📚 Exercise 3: explain a field

`kubectl explain` describes a type, or one of its fields. You name the field by
its path, with dots. Here are the fields of `spec` in a Deployment. `grep`
keeps only the titles and the field names, so the list fits on the screen:

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

Each field shows its type between `< >`: `<integer>` for a whole number,
`<boolean>` for true or false. The `-required-` mark flags a **mandatory**
field: a Deployment without `selector` or `template` is refused.

Now go down to a precise field: the interval between two tries of a readiness
probe, in the Pod's container. This time, without `grep`, the full output:

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

The description gives the unit (seconds), the default value (10) and the
minimum (1). That is what you look for when you do not know what to write.

## 📚 Exercise 4: a whole branch at once

`--recursive` shows all the fields under a path, with their sub-fields shifted
to the right. Here is how a probe makes an HTTP request:

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

At a glance: `port` is mandatory, `path` is not. `<[]HTTPHeader>` means a
**list** of headers. `enum:` gives the only accepted values. So to write an
HTTP probe, you only need `httpGet`, with at least a `port`.

## 📚 Exercise 5: a type nobody introduced to you

You can add a type to the cluster with a **CustomResourceDefinition** (CRD).
Create the trial type `Recette`, in the `cuisine.exemple.fr` group. Its
descriptions are written in French: "Ce que la recette demande" means "What
the recipe asks for", "Le nom du plat" means "The name of the dish", and "Le
nombre de personnes, de 1 a 12" means "The number of people, from 1 to 12":

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

The cluster takes a few seconds to publish a new type. Wait until it is ready:

```bash
kubectl wait --for=condition=Established crd/recettes.cuisine.exemple.fr --timeout=60s; sleep 5
```

```text
customresourcedefinition.apiextensions.k8s.io/recettes.cuisine.exemple.fr condition met
```

Now forget that you wrote it, and act as if the type were unknown. First, its
line in `api-resources`:

```bash
kubectl api-resources --api-group=cuisine.exemple.fr
```

```text
NAME       SHORTNAMES   APIVERSION                   NAMESPACED   KIND
recettes   rec          cuisine.exemple.fr/v1beta1   true         Recette
```

A manifest of this type therefore starts with `apiVersion:
cuisine.exemple.fr/v1beta1` and `kind: Recette`. The group name did not tell
the version: this column gives it. Then, its fields:

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

`explain` reads the description written by the author of the type. Both fields
are mandatory, and the description of `portions` tells its format.

## 📚 Exercise 6: what an object cannot leave out

Create the scratch namespace, then a recipe **without** `portions`:

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

The cluster refuses the object and names the missing field: that is the
`-required-` seen in `explain`. Add it:

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

The `rec` shortcut, read in the `SHORTNAMES` column, works like `cm` or
`deploy`.

## 📚 Exercise 7: the full inventory of a namespace

Add a ConfigMap to the namespace, then ask for "all":

```bash
kubectl create configmap reglages --from-literal=a=1 -n essai-api
kubectl get all -n essai-api
```

```text
configmap/reglages created
No resources found in essai-api namespace.
```

"No resources", while the namespace holds a recipe and a ConfigMap. `kubectl
get all` only looks at a short list of types (Pods, Services, Deployments and a
few others). It sees neither ConfigMaps nor the types added by a CRD.

For a real inventory, ask `api-resources` for the types that can be
**listed** (`--verbs=list`) **and live in a namespace** (`--namespaced`), with
their name only (`-o name`). Then query them one by one with `xargs`. Events
(`events`) are left out because there are too many of them. `endpoints` is
left out too: this type is deprecated since Kubernetes 1.33 in favour of
EndpointSlices, and reading it prints a warning:

```bash
kubectl api-resources --verbs=list --namespaced -o name | grep -v -E '^(events|endpoints)' | xargs -n1 kubectl get -n essai-api --ignore-not-found -o name
```

```text
configmap/kube-root-ca.crt
configmap/reglages
serviceaccount/default
recette.cuisine.exemple.fr/soupe
```

This time, everything is there. `kube-root-ca.crt` and the `default` account
are created automatically in every namespace. `--ignore-not-found` avoids a
message for each type missing from the namespace.

## 🧹 Clean up

Delete the scratch namespace, then the `Recette` type:

```bash
kubectl delete namespace essai-api; kubectl delete crd recettes.cuisine.exemple.fr
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

Your turn, on your own this time: discover a backup type set up by the lab,
create a backup with the right fields, add a probe to a Deployment, and take
the inventory of a namespace.

```bash
dsoxlab run k8s-explorer-l-api
dsoxlab challenge k8s-explorer-l-api
```
