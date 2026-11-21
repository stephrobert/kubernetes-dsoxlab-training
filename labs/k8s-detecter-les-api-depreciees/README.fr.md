# Détecter et migrer les API retirées

La leçon montre comment Kubernetes retire des versions d'API, et comment
retrouver les manifestes qui s'en servent encore. Ce cours vous fait migrer
deux manifestes d'essai, sur des types que la leçon et le challenge
n'utilisent pas, et ajoute des cas qu'ils ne montrent pas : lire les versions
servies par groupe, le message d'une version retirée, une migration qui ne
change que la version, et un champ qui a changé de forme.

Vous travaillez dans un répertoire d'essai, `~/essai-api`, et un namespace
d'essai, `essai-api`, avec un Role `lecteur` et une EndpointSlice `repere`.
Le challenge porte sur un autre dépôt de manifestes : vous le ferez seul, à
la fin.

Page associée : [Dépréciations des API Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/api-deprecations/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-detecter-les-api-depreciees
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : les versions que l'API sert aujourd'hui

Listez les versions servies pour trois groupes d'API :

```bash
kubectl api-versions | grep -E '^(rbac|discovery|scheduling)'
```

```text
discovery.k8s.io/v1
rbac.authorization.k8s.io/v1
scheduling.k8s.io/v1
```

Une seule version par groupe : `v1`. Les versions `v1beta1` de ces groupes ont
été retirées. Pour savoir sous quelle version un type est servi, demandez-le
par groupe :

```bash
kubectl api-resources --api-group=discovery.k8s.io; kubectl api-resources --api-group=rbac.authorization.k8s.io
```

```text
NAME             SHORTNAMES   APIVERSION            NAMESPACED   KIND
endpointslices                discovery.k8s.io/v1   true         EndpointSlice
NAME                  SHORTNAMES   APIVERSION                     NAMESPACED   KIND
clusterrolebindings                rbac.authorization.k8s.io/v1   false        ClusterRoleBinding
clusterroles                       rbac.authorization.k8s.io/v1   false        ClusterRole
rolebindings                       rbac.authorization.k8s.io/v1   true         RoleBinding
roles                              rbac.authorization.k8s.io/v1   true         Role
```

La colonne `APIVERSION` donne la version à écrire dans un manifeste. C'est la
référence : pas une documentation, pas un ancien manifeste, mais ce que le
cluster sert.

## ⛔ Exercice 2 : une version retirée, et ce que dit l'API

Écrivez un Role en `rbac.authorization.k8s.io/v1beta1`, et demandez à l'API
server s'il l'accepte, sans rien créer (`--dry-run=server`) :

```bash
kubectl create namespace essai-api; mkdir -p ~/essai-api; cat > ~/essai-api/role.yaml <<'YAML'
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: Role
metadata:
  name: lecteur
  namespace: essai-api
rules:
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list]
YAML
kubectl apply --dry-run=server -f ~/essai-api/role.yaml
```

```text
namespace/essai-api created
error: resource mapping not found for name: "lecteur" namespace: "essai-api" from "/home/ansible/essai-api/role.yaml": no matches for kind "Role" in version "rbac.authorization.k8s.io/v1beta1"
ensure CRDs are installed first
```

`no matches for kind "Role" in version "rbac.authorization.k8s.io/v1beta1"`.
L'API ne connaît plus ce couple type et version. La seconde ligne parle des
CRD, parce que le même message sert pour un type inconnu : ici, ce n'est pas
le problème.

## ✔️ Exercice 3 : une migration qui ne change que la version

Pour un Role, rien d'autre n'a changé entre `v1beta1` et `v1`. Remplacez la
version, et redemandez :

```bash
sed -i 's#rbac.authorization.k8s.io/v1beta1#rbac.authorization.k8s.io/v1#' ~/essai-api/role.yaml; kubectl apply --dry-run=server -f ~/essai-api/role.yaml
```

```text
role.rbac.authorization.k8s.io/lecteur created (server dry run)
```

Accepté. Pour beaucoup de types, la migration se limite à la ligne
`apiVersion`. Ce n'est pas toujours le cas.

## 🔀 Exercice 4 : un champ qui a changé de forme

En `discovery.k8s.io/v1beta1`, une EndpointSlice rangeait le nœud de chaque
adresse dans un champ `topology`. Écrivez une EndpointSlice en `v1`, mais
avec ce champ hérité :

```bash
cat > ~/essai-api/repere.yaml <<'YAML'
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: repere
  namespace: essai-api
addressType: IPv4
endpoints:
  - addresses: [10.244.0.50]
    topology:
      kubernetes.io/hostname: k8s-w1.lab
ports:
  - port: 80
YAML
kubectl apply --dry-run=server -f ~/essai-api/repere.yaml
```

```text
Error from server (BadRequest): error when creating "/home/ansible/essai-api/repere.yaml": EndpointSlice in version "v1" cannot be handled as a EndpointSlice: strict decoding error: unknown field "endpoints[0].topology"
```

La version passe, le champ non : `unknown field "endpoints[0].topology"`. Le
contrôle strict de l'API refuse un champ qu'il ne connaît pas, au lieu de
l'ignorer. Demandez quels champs la version `v1` attend :

```bash
kubectl explain endpointslice.endpoints --api-version=discovery.k8s.io/v1 | grep -E '^  [a-zA-Z]+' 
```

```text
  addresses	<[]string> -required-
  conditions	<EndpointConditions>
  deprecatedTopology	<map[string]string>
  hints	<EndpointHints>
  hostname	<string>
  nodeName	<string>
  targetRef	<ObjectReference>
  zone	<string>
```

Le nœud a maintenant son propre champ, `nodeName`, et l'ancien `topology` est
devenu `deprecatedTopology`. Corrigez le manifeste et redemandez :

```bash
sed -i 's#    topology:#    nodeName: k8s-w1.lab#; /kubernetes.io\/hostname/d' ~/essai-api/repere.yaml; sed -n '/endpoints:/,/ports:/p' ~/essai-api/repere.yaml; kubectl apply --dry-run=server -f ~/essai-api/repere.yaml
```

```text
endpoints:
  - addresses: [10.244.0.50]
    nodeName: k8s-w1.lab
ports:
endpointslice.discovery.k8s.io/repere created (server dry run)
```

Accepté. Changer la version ne suffit pas toujours : il faut lire l'erreur
jusqu'au bout, puis `kubectl explain` sur la version visée.

## 🧹 Nettoyage

Supprimez le namespace et le répertoire d'essai :

```bash
kubectl delete namespace essai-api; rm -rf ~/essai-api
```

```text
namespace "essai-api" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-detecter-les-api-depreciees
dsoxlab check k8s-detecter-les-api-depreciees
```

```text
╭─ Résultat : k8s-detecter-les-api-depreciees ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un dépôt de manifestes anciens, à trier et à
migrer sans rien changer à ce qu'ils décrivent.

```bash
dsoxlab run k8s-detecter-les-api-depreciees
dsoxlab challenge k8s-detecter-les-api-depreciees
```
