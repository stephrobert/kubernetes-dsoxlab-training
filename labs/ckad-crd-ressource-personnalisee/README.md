# Use a custom resource, read its schema refusals, unblock it

The lesson shows a CustomResourceDefinition (CRD), which adds a new object
type to the API, and resources of that type. This course has you write your
own CRD and adds cases the lesson does not show: a default value set by the
API, a list of allowed values, a consistency rule in CEL (Kubernetes'
expression language), a category that groups types, and a second version that
makes the first one deprecated.

You work with a scratch CRD, `inventaires.essai.lab` (kind `Inventaire`,
"inventory"), in the `essai-crd` namespace. The challenge is about another
CRD: you will do it on your own, at the end.

Related page: [Operators and CRDs for developers](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/operators-crds-developpeurs/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-crd-ressource-personnalisee
```

You are now connected to `k8s-kind.lab`, a machine that runs a kind cluster.
Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.0 (kind cluster).

## 📐 Exercise 1: a CRD with a default, a list of values and a CEL rule

Write a CRD to a file, then apply it. Its schema requires a `rayon` ("aisle")
field taken from a list (`enum`), gives default values to `minimum` and
`maximum`, and checks that `minimum` does not exceed `maximum`
(`x-kubernetes-validations`). The `additionalPrinterColumns` choose the
columns of `kubectl get`, and `categories` puts the type in a group:

```bash
kubectl create namespace essai-crd; cat > ~/inventaire-crd.yaml <<'YAML'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: inventaires.essai.lab
spec:
  group: essai.lab
  scope: Namespaced
  names:
    plural: inventaires
    singular: inventaire
    kind: Inventaire
    categories: [essais]
  versions:
    - name: v1
      served: true
      storage: true
      additionalPrinterColumns:
        - {name: Rayon, type: string, jsonPath: .spec.rayon}
        - {name: Min, type: integer, jsonPath: .spec.minimum}
        - {name: Max, type: integer, jsonPath: .spec.maximum}
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: [rayon]
              x-kubernetes-validations:
                - rule: "self.minimum <= self.maximum"
                  message: "minimum doit rester inférieur ou égal à maximum"
              properties:
                rayon:
                  type: string
                  enum: [frais, sec, surgele]
                minimum: {type: integer, default: 1}
                maximum: {type: integer, default: 100}
YAML
kubectl apply -f ~/inventaire-crd.yaml; kubectl wait --for=condition=Established crd/inventaires.essai.lab --timeout=60s
```

```text
namespace/essai-crd created
customresourcedefinition.apiextensions.k8s.io/inventaires.essai.lab created
customresourcedefinition.apiextensions.k8s.io/inventaires.essai.lab condition met
```

`Established`: the API knows the new type. Create an Inventaire that only
gives its aisle:

```bash
cat <<'YAML' | kubectl apply -n essai-crd -f -
apiVersion: essai.lab/v1
kind: Inventaire
metadata:
  name: rayon-sec
spec:
  rayon: sec
YAML
kubectl get inventaires -n essai-crd; kubectl get inventaire rayon-sec -n essai-crd -o jsonpath='{.spec}{"\n"}'
```

```text
inventaire.essai.lab/rayon-sec created
NAME        RAYON   MIN   MAX
rayon-sec   sec     1     100
{"maximum":100,"minimum":1,"rayon":"sec"}
```

The table shows the declared columns. The stored `spec` contains `minimum: 1`
and `maximum: 100`, which you did not write: the API set the schema's default
values when storing the object.

## 🚫 Exercise 2: the refusals of the list and of the CEL rule

Create an Inventaire for an aisle that is not in the list:

```bash
cat <<'YAML' | kubectl apply -n essai-crd -f -
apiVersion: essai.lab/v1
kind: Inventaire
metadata:
  name: rayon-boissons
spec:
  rayon: boissons
YAML
```

```text
The Inventaire "rayon-boissons" is invalid: 
* spec.rayon: Unsupported value: "boissons": supported values: "frais", "sec", "surgele"
* <nil>: Invalid value: null: some validation rules were not checked because the object was invalid; correct the existing errors to complete validation
```

The refusal names the field, the faulty value and the allowed values. The
second line says the CEL rules were not checked: the API stops at type errors
before evaluating the rules. Now create an Inventaire whose minimum exceeds
its maximum:

```bash
cat <<'YAML' | kubectl apply -n essai-crd -f -
apiVersion: essai.lab/v1
kind: Inventaire
metadata:
  name: rayon-frais
spec:
  rayon: frais
  minimum: 50
  maximum: 10
YAML
```

```text
The Inventaire "rayon-frais" is invalid: spec: Invalid value: minimum doit rester inférieur ou égal à maximum
```

The refusal repeats the `message` declared in the rule (here in French: "the
minimum must stay lower than or equal to the maximum"). Write messages that
say what to fix: that is all the CRD's users will see. In both cases, nothing
was created.

## 🗂️ Exercise 3: a category that groups

The CRD declared the `essais` category. Ask for it as if it were a type:

```bash
kubectl get essais -n essai-crd
```

```text
NAME        RAYON   MIN   MAX
rayon-sec   sec     1     100
```

A category lists at once every type that declares it. It is the same
mechanism as `kubectl get all`, which is a category that Pods, Services,
Deployments and other common types belong to.

## 🏷️ Exercise 4: a second version, the first one deprecated

A CRD can serve several versions of its API, only one of which is used for
storage. The Python script adds an identical `v2` version, which becomes the
storage version, and marks `v1` as deprecated with a warning (`servie` means
"served", `stockage` "storage", `dépréciée` "deprecated"):

```bash
cat > ~/inventaire-v2.py <<'PY'
import sys, yaml
crd = yaml.safe_load(open(sys.argv[1]))
v1 = crd['spec']['versions'][0]
v1['storage'] = False
v1['deprecated'] = True
v1['deprecationWarning'] = 'essai.lab/v1 Inventaire est déprécié, passez à essai.lab/v2'
v2 = yaml.safe_load(yaml.safe_dump(v1))
v2.update(name='v2', storage=True, deprecated=False)
v2.pop('deprecationWarning')
crd['spec']['versions'].append(v2)
print(yaml.safe_dump(crd, allow_unicode=True))
PY
python3 ~/inventaire-v2.py ~/inventaire-crd.yaml | kubectl apply -f -; kubectl get crd inventaires.essai.lab -o jsonpath='{range .spec.versions[*]}{.name} servie={.served} stockage={.storage} dépréciée={.deprecated}{"\n"}{end}'
```

```text
customresourcedefinition.apiextensions.k8s.io/inventaires.essai.lab configured
v1 servie=true stockage=false dépréciée=true
v2 servie=true stockage=true dépréciée=
```

Both versions are served, `v2` holds storage, `v1` is deprecated. Read the
resource through each of the two versions:

```bash
kubectl get inventaires.v1.essai.lab -n essai-crd; kubectl get inventaires.v2.essai.lab -n essai-crd
```

```text
Warning: essai.lab/v1 Inventaire est déprécié, passez à essai.lab/v2
NAME        RAYON   MIN   MAX
rayon-sec   sec     1     100
NAME        RAYON   MIN   MAX
rayon-sec   sec     1     100
```

The resource created in `v1` can be read in both versions. Read through `v1`,
the API sends the declared warning, which kubectl shows as a `Warning`. This
is how you announce the end of a version without breaking anything.

## 🧹 Clean-up

Delete the CRD, then the namespace and the two files. Deleting a CRD also
deletes every resource of that type:

```bash
kubectl delete crd inventaires.essai.lab; kubectl delete namespace essai-crd; rm -f ~/inventaire-crd.yaml ~/inventaire-v2.py
```

```text
customresourcedefinition.apiextensions.k8s.io "inventaires.essai.lab" deleted
namespace "essai-crd" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-crd-ressource-personnalisee
dsoxlab check ckad-crd-ressource-personnalisee
```

```text
╭─ Result: ckad-crd-ressource-personnalisee ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests           │
╰────────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: custom resources to create, change and
remove, and a schema refusal to read.

```bash
dsoxlab run ckad-crd-ressource-personnalisee
dsoxlab challenge ckad-crd-ressource-personnalisee
```
