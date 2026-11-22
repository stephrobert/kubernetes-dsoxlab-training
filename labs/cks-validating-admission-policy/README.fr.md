# Faire refuser un objet par le cluster avec une ValidatingAdmissionPolicy

La leçon montre comment écrire une ValidatingAdmissionPolicy en CEL, la lier
à des namespaces et la déployer en `Audit`, `Warn` puis `Deny`. Ce cours
ajoute quatre cas qu'elle ne montre pas : une politique sans liaison qui
n'agit sur rien, une politique sur des ConfigMaps plutôt que des Pods, un
objet créé avant la liaison et refusé seulement à sa prochaine modification,
et l'erreur qu'on obtient en lisant un champ absent sans `has()`.

Vous travaillez dans le namespace `essai-vap`, avec une politique qui exige un
label `equipe` sur les ConfigMaps. Le challenge porte sur un autre namespace
et une autre règle : vous le ferez seul, à la fin.

Page associée : [ValidatingAdmissionPolicy](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/validating-admission-policy/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-validating-admission-policy
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2.

## 📜 Exercice 1 : une politique seule ne fait rien

Créez le namespace d'essai et une politique qui exige le label `equipe` sur
toute ConfigMap créée ou modifiée. `has()` vérifie d'abord que l'objet porte
des labels, avant d'y chercher `equipe`. Créez ensuite une ConfigMap sans
label :

```bash
kubectl create namespace essai-vap; cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-etiquette-equipe
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [configmaps]
  validations:
    - expression: 'has(object.metadata.labels) && "equipe" in object.metadata.labels'
      message: "une ConfigMap de essai-vap porte le label equipe"
YAML
kubectl create configmap sans-label -n essai-vap --from-literal=a=1
```

```text
namespace/essai-vap created
validatingadmissionpolicy.admissionregistration.k8s.io/essai-etiquette-equipe created
configmap/sans-label created
```

La politique est créée, et la ConfigMap aussi : une politique ne dit que
**quoi** vérifier. Tant qu'aucune liaison ne dit **où** l'appliquer, elle
n'agit sur rien, et rien ne vous en avertit.

## 🔗 Exercice 2 : la liaison l'active, sur un namespace

Liez la politique au seul namespace `essai-vap`, en mode `Deny`, puis créez
une seconde ConfigMap sans label :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: essai-etiquette-equipe
spec:
  policyName: essai-etiquette-equipe
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: essai-vap}
YAML
sleep 3; kubectl create configmap sans-label-2 -n essai-vap --from-literal=a=1
```

```text
validatingadmissionpolicybinding.admissionregistration.k8s.io/essai-etiquette-equipe created
error: failed to create configmap: configmaps "sans-label-2" is forbidden: ValidatingAdmissionPolicy 'essai-etiquette-equipe' with binding 'essai-etiquette-equipe' denied request: une ConfigMap de essai-vap porte le label equipe
```

Refusée, avec le message de la politique. Créez maintenant une ConfigMap qui
porte le label dans `essai-vap`, et une ConfigMap sans label dans `default` :

```bash
kubectl create configmap avec-label -n essai-vap --from-literal=a=1 --dry-run=client -o yaml | kubectl label --local -f - equipe=accueil -o yaml | kubectl apply -f -; kubectl create configmap ailleurs -n default --from-literal=a=1; kubectl delete configmap ailleurs -n default >/dev/null
```

```text
configmap/avec-label created
configmap/ailleurs created
```

Les deux passent : la première respecte la règle, la seconde est hors du
namespace visé par la liaison. Le `namespaceSelector` de la liaison borne
l'effet de la politique.

## ⏳ Exercice 3 : un objet d'avant la liaison

La ConfigMap `sans-label` de l'exercice 1 existe toujours, sans label. Une
politique ne revient jamais sur les objets existants : elle juge ce qui
arrive à l'API server. Modifiez-la, même d'une simple annotation :

```bash
kubectl get configmap sans-label -n essai-vap -o name; kubectl annotate configmap sans-label -n essai-vap revue=faite 2>&1 | cut -c1-220
```

```text
configmap/sans-label
The configmaps "sans-label" is invalid: : ValidatingAdmissionPolicy 'essai-etiquette-equipe' with binding 'essai-etiquette-equipe' denied request: une ConfigMap de essai-vap porte le label equipe
```

Refusée : la règle porte aussi sur `UPDATE`, et la ConfigMap ne la respecte
pas. Un objet ancien passe donc inaperçu jusqu'à sa prochaine modification,
qui échoue alors pour une raison que son auteur n'a pas causée. Avant de
poser une liaison en `Deny`, cherchez les objets existants qui violent la
règle.

## ⚠️ Exercice 4 : sans has(), une erreur au lieu d'un refus clair

Remplacez l'expression par une version sans `has()`, puis créez une ConfigMap
sans aucun label :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-etiquette-equipe
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [configmaps]
  validations:
    - expression: '"equipe" in object.metadata.labels'
      message: "une ConfigMap de essai-vap porte le label equipe"
YAML
sleep 3; kubectl create configmap sans-label-3 -n essai-vap --from-literal=a=1 2>&1 | cut -c1-400
```

```text
validatingadmissionpolicy.admissionregistration.k8s.io/essai-etiquette-equipe configured
error: failed to create configmap: configmaps "sans-label-3" is forbidden: ValidatingAdmissionPolicy 'essai-etiquette-equipe' with binding 'essai-etiquette-equipe' denied request: expression '"equipe" in object.metadata.labels' resulted in error: no such key: labels
```

La ConfigMap est refusée, mais pas par le message de la politique : l'API
server n'a pas pu **calculer** l'expression (`no such key: labels`), parce
qu'un objet sans label n'a pas de champ `labels`. Avec `failurePolicy: Fail`,
une erreur de calcul refuse la requête. Avec `Ignore`, elle l'aurait laissée
passer. Protégez chaque accès à un champ facultatif par `has()`.

## 🧹 Nettoyage

Supprimez la liaison, la politique, puis le namespace d'essai :

```bash
kubectl delete validatingadmissionpolicybinding essai-etiquette-equipe; kubectl delete validatingadmissionpolicy essai-etiquette-equipe; kubectl delete namespace essai-vap
```

```text
validatingadmissionpolicybinding.admissionregistration.k8s.io "essai-etiquette-equipe" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "essai-etiquette-equipe" deleted
namespace "essai-vap" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-validating-admission-policy
dsoxlab check cks-validating-admission-policy
```

```text
╭─ Résultat : cks-validating-admission-policy ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : faire refuser par le cluster, dans un seul
namespace, les Pods dont l'image n'est pas épinglée par son digest.

```bash
dsoxlab run cks-validating-admission-policy
dsoxlab challenge cks-validating-admission-policy
```
