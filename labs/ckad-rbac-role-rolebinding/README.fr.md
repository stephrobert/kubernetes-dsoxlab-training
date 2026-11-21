# Donner un accès en lecture seule aux Pods avec RBAC

La leçon montre RBAC : un Role qui liste des droits, un RoleBinding qui les
donne à un utilisateur. Ce cours ajoute des cas que la leçon ne montre pas :
un droit sur un seul objet nommé, un groupe d'utilisateurs, un ClusterRole qui
se remplit à partir d'autres, la règle qui interdit de donner un droit qu'on
n'a pas, et des droits sur des adresses de l'API plutôt que sur des objets.

Vous travaillez dans un namespace d'essai, `essai-rbac`, avec un utilisateur
fictif `comptable`, un groupe `equipe-compta` et un ServiceAccount `delegue`.
Le challenge porte sur un autre utilisateur et d'autres objets : vous le
ferez seul, à la fin.

Page associée : [RBAC](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-rbac-role-rolebinding
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, avec les droits
d'administrateur.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Pour tester les droits d'un autre, ce cours utilise `kubectl auth can-i` avec
`--as` : vous demandez à l'API ce qu'elle répondrait à cet utilisateur. Le
code de retour vaut 1 quand la dernière réponse est `no`.

Créez le namespace et deux ConfigMaps :

```bash
kubectl create namespace essai-rbac; kubectl create configmap reglages -n essai-rbac --from-literal=a=1; kubectl create configmap brouillon -n essai-rbac --from-literal=b=2
```

```text
namespace/essai-rbac created
configmap/reglages created
configmap/brouillon created
```

## 🎯 Exercice 1 : un droit sur un seul objet

`--resource-name` limite un droit à un objet nommé. Donnez à `comptable` le
droit de lire la ConfigMap `reglages`, et rien d'autre :

```bash
kubectl create role lire-reglages -n essai-rbac --verb=get --resource=configmaps --resource-name=reglages; kubectl create rolebinding comptable-reglages -n essai-rbac --role=lire-reglages --user=comptable
```

```text
role.rbac.authorization.k8s.io/lire-reglages created
rolebinding.rbac.authorization.k8s.io/comptable-reglages created
```

```bash
for c in reglages brouillon; do printf 'get %s : ' $c; kubectl auth can-i get configmap/$c -n essai-rbac --as=comptable; done; printf 'list configmaps : '; kubectl auth can-i list configmaps -n essai-rbac --as=comptable
```

```text
get reglages : yes
get brouillon : no
list configmaps : no
```

`reglages` oui, `brouillon` non. Et `list` est refusé aussi : un droit limité
à des noms ne permet pas de lister, puisque la liste montrerait tous les
objets. Pour qu'un outil puisse lister puis lire un seul objet, il faut deux
règles.

## 👥 Exercice 2 : un groupe, et l'usurpation qui le porte

Donnez le ClusterRole `view`, livré avec Kubernetes, au groupe
`equipe-compta`, dans le namespace d'essai. Testez ensuite `comptable` seul,
puis `comptable` membre du groupe (`--as-group`) :

```bash
kubectl create rolebinding equipe-lit -n essai-rbac --clusterrole=view --group=equipe-compta; printf 'sans groupe : '; kubectl auth can-i list pods -n essai-rbac --as=comptable; printf 'avec groupe : '; kubectl auth can-i list pods -n essai-rbac --as=comptable --as-group=equipe-compta
```

```text
rolebinding.rbac.authorization.k8s.io/equipe-lit created
sans groupe : no
avec groupe : yes
```

Le droit vient du groupe, pas de l'utilisateur. Les groupes ne sont pas des
objets de Kubernetes : c'est le moyen d'authentification (certificat, jeton,
fournisseur d'identité) qui dit à quels groupes appartient la personne. Un
RoleBinding vers un groupe s'applique donc à tous ses membres, présents et à
venir.

## 🧩 Exercice 3 : un ClusterRole qui se remplit tout seul

Un ClusterRole avec `aggregationRule` n'a pas de règles à lui : il reçoit
celles des ClusterRoles qui portent une étiquette donnée. Créez-en un, vide :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: essai-auditeur
aggregationRule:
  clusterRoleSelectors:
    - matchLabels: {essai.lab/auditeur: "oui"}
rules: []
YAML
kubectl get clusterrole essai-auditeur -o jsonpath='règles={.rules}{"\n"}'
```

```text
clusterrole.rbac.authorization.k8s.io/essai-auditeur created
règles=null
```

`règles=null` : il est vide. Créez un ClusterRole qui lit les événements, et
posez-lui l'étiquette attendue :

```bash
kubectl create clusterrole essai-lire-events --verb=get,list --resource=events; kubectl label clusterrole essai-lire-events essai.lab/auditeur=oui; sleep 3; kubectl get clusterrole essai-auditeur -o jsonpath='{range .rules[*]}{.resources} {.verbs}{"\n"}{end}'
```

```text
clusterrole.rbac.authorization.k8s.io/essai-lire-events created
clusterrole.rbac.authorization.k8s.io/essai-lire-events labeled
["events"] ["get","list"]
```

`essai-auditeur` a reçu les règles de `essai-lire-events`, sans qu'on le
modifie. Les ClusterRoles `admin`, `edit` et `view` du cluster sont construits
de cette façon : ils reçoivent les droits sur une ressource ajoutée au cluster
dès qu'un ClusterRole porte leur étiquette d'agrégation.

## 🛑 Exercice 4 : on ne donne pas ce qu'on n'a pas

Créez un ServiceAccount `delegue` qui a le droit de créer des Roles dans le
namespace, mais aucun droit sur les Secrets :

```bash
kubectl create serviceaccount delegue -n essai-rbac; kubectl create role gerer-roles -n essai-rbac --verb=create,get,list --resource=roles,rolebindings; kubectl create rolebinding delegue-roles -n essai-rbac --role=gerer-roles --serviceaccount=essai-rbac:delegue
```

```text
serviceaccount/delegue created
role.rbac.authorization.k8s.io/gerer-roles created
rolebinding.rbac.authorization.k8s.io/delegue-roles created
```

Au nom de `delegue`, essayez de créer un Role qui donne tous les droits sur
les Secrets :

```bash
kubectl create role tout-sur-secrets -n essai-rbac --verb='*' --resource=secrets --as=system:serviceaccount:essai-rbac:delegue 2>&1 | cut -c1-220
```

```text
Error from server (Forbidden): roles.rbac.authorization.k8s.io "tout-sur-secrets" is forbidden: user "system:serviceaccount:essai-rbac:delegue" (groups=["system:serviceaccounts" "system:serviceaccounts:essai-rbac" "syste
{APIGroups:[""], Resources:["secrets"], Verbs:["*"]}
```

Refusé, alors que `delegue` a le droit de créer des Roles. RBAC empêche
l'escalade : on ne peut écrire dans un Role que des droits qu'on possède
déjà. Le message liste la règle en trop. Un Role qui reste dans ses droits
passe :

```bash
kubectl create role lire-roles -n essai-rbac --verb=get --resource=roles --as=system:serviceaccount:essai-rbac:delegue
```

```text
role.rbac.authorization.k8s.io/lire-roles created
```

## 🌐 Exercice 5 : des droits sur des URL, pas sur des objets

Certaines adresses de l'API ne sont pas des objets : `/healthz`, `/metrics`.
Testez-les pour `comptable` :

```bash
printf 'comptable /healthz : '; kubectl auth can-i get /healthz --as=comptable; printf 'comptable /metrics : '; kubectl auth can-i get /metrics --as=comptable
```

```text
comptable /healthz : yes
comptable /metrics : no
```

`/healthz` est ouvert à tous les utilisateurs authentifiés par un rôle livré
avec le cluster. `/metrics`, lui, est fermé. Ces adresses se donnent avec
`--non-resource-url`, et seulement dans un ClusterRole, puisqu'elles
n'appartiennent à aucun namespace :

```bash
kubectl create clusterrole essai-metriques --verb=get --non-resource-url=/metrics; kubectl create clusterrolebinding essai-metriques --clusterrole=essai-metriques --user=comptable; printf 'comptable /metrics : '; kubectl auth can-i get /metrics --as=comptable
```

```text
clusterrole.rbac.authorization.k8s.io/essai-metriques created
clusterrolebinding.rbac.authorization.k8s.io/essai-metriques created
comptable /metrics : yes
```

## 🧹 Nettoyage

Supprimez le namespace d'essai, puis les objets RBAC qui n'appartiennent à
aucun namespace :

```bash
kubectl delete namespace essai-rbac; kubectl delete clusterrole essai-auditeur essai-lire-events essai-metriques; kubectl delete clusterrolebinding essai-metriques
```

```text
namespace "essai-rbac" deleted
clusterrole.rbac.authorization.k8s.io "essai-auditeur" deleted
clusterrole.rbac.authorization.k8s.io "essai-lire-events" deleted
clusterrole.rbac.authorization.k8s.io "essai-metriques" deleted
clusterrolebinding.rbac.authorization.k8s.io "essai-metriques" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-rbac-role-rolebinding
dsoxlab check ckad-rbac-role-rolebinding
```

```text
╭─ Résultat : ckad-rbac-role-rolebinding ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests        │
╰─────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une utilisatrice qui doit pouvoir lire les Pods
d'un namespace et leurs journaux, et rien d'autre.

```bash
dsoxlab run ckad-rbac-role-rolebinding
dsoxlab challenge ckad-rbac-role-rolebinding
```
