# Utiliser une ressource personnalisée, lire les refus de son schéma, la débloquer

La leçon montre une CustomResourceDefinition (CRD), qui ajoute un nouveau type
d'objet à l'API, et des ressources de ce type. Ce cours vous fait écrire
votre propre CRD et ajoute des cas que la leçon ne montre pas : une valeur par
défaut posée par l'API, une liste de valeurs permises, une règle de cohérence
en CEL (le langage d'expressions de Kubernetes), une catégorie qui regroupe
des types, et une seconde version qui rend la première dépréciée.

Vous travaillez avec une CRD d'essai, `inventaires.essai.lab` (type
`Inventaire`), dans le namespace `essai-crd`. Le challenge porte sur une autre
CRD : vous le ferez seul, à la fin.

Page associée : [Opérateurs et CRD pour les développeurs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operators-crds-developpeurs/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-crd-ressource-personnalisee
```

Vous êtes maintenant connecté à `k8s-kind.lab`, une machine qui fait tourner
un cluster kind. Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.0 (cluster kind).

## 📐 Exercice 1 : une CRD avec défaut, liste de valeurs et règle CEL

Écrivez une CRD dans un fichier, puis appliquez-la. Son schéma exige un
champ `rayon` pris dans une liste (`enum`), donne des valeurs par défaut à
`minimum` et `maximum`, et vérifie que `minimum` ne dépasse pas `maximum`
(`x-kubernetes-validations`). Les `additionalPrinterColumns` choisissent les
colonnes de `kubectl get`, et `categories` range le type dans un groupe :

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

`Established` : l'API connaît le nouveau type. Créez un Inventaire qui ne
donne que son rayon :

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

Le tableau montre les colonnes déclarées. Le `spec` enregistré contient
`minimum: 1` et `maximum: 100`, que vous n'avez pas écrits : l'API a posé les
valeurs par défaut du schéma à l'enregistrement.

## 🚫 Exercice 2 : les refus de la liste et de la règle CEL

Créez un Inventaire pour un rayon qui n'est pas dans la liste :

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

Le refus nomme le champ, la valeur fautive et les valeurs permises. La
seconde ligne dit que les règles CEL n'ont pas été vérifiées : l'API s'arrête
aux erreurs de type avant d'évaluer les règles. Créez maintenant un Inventaire
dont le minimum dépasse le maximum :

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

Le refus reprend le `message` déclaré dans la règle. Écrivez des messages qui
disent quoi corriger : c'est tout ce que verra l'utilisateur de la CRD. Dans
les deux cas, rien n'a été créé.

## 🗂️ Exercice 3 : une catégorie qui regroupe

La CRD a déclaré la catégorie `essais`. Demandez-la comme un type :

```bash
kubectl get essais -n essai-crd
```

```text
NAME        RAYON   MIN   MAX
rayon-sec   sec     1     100
```

Une catégorie liste d'un coup tous les types qui la déclarent. C'est le même
mécanisme que `kubectl get all`, qui est une catégorie à laquelle appartiennent
les Pods, Services, Deployments et autres types courants.

## 🏷️ Exercice 4 : une seconde version, la première dépréciée

Une CRD peut servir plusieurs versions de son API, dont une seule sert au
stockage. Le script Python ajoute une version `v2`, identique, qui devient la
version de stockage, et marque `v1` comme dépréciée avec un avertissement :

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

Les deux versions sont servies, `v2` porte le stockage, `v1` est dépréciée.
Lisez la ressource par chacune des deux versions :

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

La ressource créée en `v1` se lit dans les deux versions. Lue par `v1`, l'API
envoie l'avertissement déclaré, que kubectl affiche en `Warning`. C'est ainsi
qu'on annonce la fin d'une version sans rien casser.

## 🧹 Nettoyage

Supprimez la CRD, puis le namespace et les deux fichiers. Supprimer une CRD
supprime aussi toutes les ressources de ce type :

```bash
kubectl delete crd inventaires.essai.lab; kubectl delete namespace essai-crd; rm -f ~/inventaire-crd.yaml ~/inventaire-v2.py
```

```text
customresourcedefinition.apiextensions.k8s.io "inventaires.essai.lab" deleted
namespace "essai-crd" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-crd-ressource-personnalisee
dsoxlab check ckad-crd-ressource-personnalisee
```

```text
╭─ Résultat : ckad-crd-ressource-personnalisee ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests              │
╰───────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : des ressources personnalisées à créer, modifier et
retirer, et un refus du schéma à lire.

```bash
dsoxlab run ckad-crd-ressource-personnalisee
dsoxlab challenge ckad-crd-ressource-personnalisee
```
