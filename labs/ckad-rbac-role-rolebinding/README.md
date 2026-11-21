# Grant read-only access to Pods with RBAC

The lesson shows RBAC: a Role that lists rights, a RoleBinding that gives
them to a user. This course adds cases the lesson does not show: a right on a
single named object, a group of users, a ClusterRole that fills itself from
others, the rule that forbids giving a right you do not have, and rights on
API addresses rather than on objects.

You work in a scratch namespace, `essai-rbac`, with a fictitious user
`comptable` ("accountant"), a group `equipe-compta` ("accounting-team") and a
ServiceAccount `delegue` ("delegate"). The challenge is about another user and
other objects: you will do it on your own, at the end.

Related page: [RBAC](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/rbac/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-rbac-role-rolebinding
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, with administrator
rights.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

To test someone else's rights, this course uses `kubectl auth can-i` with
`--as`: you ask the API what it would answer to that user. The exit code is 1
when the last answer is `no`.

Create the namespace and two ConfigMaps:

```bash
kubectl create namespace essai-rbac; kubectl create configmap reglages -n essai-rbac --from-literal=a=1; kubectl create configmap brouillon -n essai-rbac --from-literal=b=2
```

```text
namespace/essai-rbac created
configmap/reglages created
configmap/brouillon created
```

## 🎯 Exercise 1: a right on a single object

`--resource-name` limits a right to a named object. Give `comptable` the
right to read the `reglages` ("settings") ConfigMap, and nothing else:

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

`reglages` yes, `brouillon` ("draft") no. And `list` is refused too: a right
limited to names does not allow listing, since the list would show every
object. For a tool to list and then read a single object, you need two rules.

## 👥 Exercise 2: a group, and the impersonation that carries it

Give the `view` ClusterRole, shipped with Kubernetes, to the `equipe-compta`
group, in the scratch namespace. Then test `comptable` alone, then
`comptable` as a member of the group (`--as-group`) (`sans groupe` means
"without group", `avec groupe` "with group"):

```bash
kubectl create rolebinding equipe-lit -n essai-rbac --clusterrole=view --group=equipe-compta; printf 'sans groupe : '; kubectl auth can-i list pods -n essai-rbac --as=comptable; printf 'avec groupe : '; kubectl auth can-i list pods -n essai-rbac --as=comptable --as-group=equipe-compta
```

```text
rolebinding.rbac.authorization.k8s.io/equipe-lit created
sans groupe : no
avec groupe : yes
```

The right comes from the group, not from the user. Groups are not Kubernetes
objects: the authentication method (certificate, token, identity provider)
says which groups the person belongs to. A RoleBinding to a group therefore
applies to all its members, present and future.

## 🧩 Exercise 3: a ClusterRole that fills itself

A ClusterRole with an `aggregationRule` has no rules of its own: it receives
those of the ClusterRoles that carry a given label. Create an empty one
(`règles` means "rules"):

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

`règles=null`: it is empty. Create a ClusterRole that reads events, and give
it the expected label:

```bash
kubectl create clusterrole essai-lire-events --verb=get,list --resource=events; kubectl label clusterrole essai-lire-events essai.lab/auditeur=oui; sleep 3; kubectl get clusterrole essai-auditeur -o jsonpath='{range .rules[*]}{.resources} {.verbs}{"\n"}{end}'
```

```text
clusterrole.rbac.authorization.k8s.io/essai-lire-events created
clusterrole.rbac.authorization.k8s.io/essai-lire-events labeled
["events"] ["get","list"]
```

`essai-auditeur` received the rules of `essai-lire-events`, without being
modified. The cluster's `admin`, `edit` and `view` ClusterRoles are built this
way: they receive the rights on a resource added to the cluster as soon as a
ClusterRole carries their aggregation label.

## 🛑 Exercise 4: you cannot give what you do not have

Create a `delegue` ServiceAccount that may create Roles in the namespace, but
has no right on Secrets:

```bash
kubectl create serviceaccount delegue -n essai-rbac; kubectl create role gerer-roles -n essai-rbac --verb=create,get,list --resource=roles,rolebindings; kubectl create rolebinding delegue-roles -n essai-rbac --role=gerer-roles --serviceaccount=essai-rbac:delegue
```

```text
serviceaccount/delegue created
role.rbac.authorization.k8s.io/gerer-roles created
rolebinding.rbac.authorization.k8s.io/delegue-roles created
```

As `delegue`, try to create a Role that gives every right on Secrets:

```bash
kubectl create role tout-sur-secrets -n essai-rbac --verb='*' --resource=secrets --as=system:serviceaccount:essai-rbac:delegue 2>&1 | cut -c1-220
```

```text
Error from server (Forbidden): roles.rbac.authorization.k8s.io "tout-sur-secrets" is forbidden: user "system:serviceaccount:essai-rbac:delegue" (groups=["system:serviceaccounts" "system:serviceaccounts:essai-rbac" "syste
{APIGroups:[""], Resources:["secrets"], Verbs:["*"]}
```

Refused, although `delegue` may create Roles. RBAC prevents escalation: you
can only write into a Role rights you already hold. The message lists the
extra rule. A Role that stays within its rights goes through:

```bash
kubectl create role lire-roles -n essai-rbac --verb=get --resource=roles --as=system:serviceaccount:essai-rbac:delegue
```

```text
role.rbac.authorization.k8s.io/lire-roles created
```

## 🌐 Exercise 5: rights on URLs, not on objects

Some API addresses are not objects: `/healthz`, `/metrics`. Test them for
`comptable`:

```bash
printf 'comptable /healthz : '; kubectl auth can-i get /healthz --as=comptable; printf 'comptable /metrics : '; kubectl auth can-i get /metrics --as=comptable
```

```text
comptable /healthz : yes
comptable /metrics : no
```

`/healthz` is open to every authenticated user through a role shipped with
the cluster. `/metrics` is closed. These addresses are granted with
`--non-resource-url`, and only in a ClusterRole, since they belong to no
namespace:

```bash
kubectl create clusterrole essai-metriques --verb=get --non-resource-url=/metrics; kubectl create clusterrolebinding essai-metriques --clusterrole=essai-metriques --user=comptable; printf 'comptable /metrics : '; kubectl auth can-i get /metrics --as=comptable
```

```text
clusterrole.rbac.authorization.k8s.io/essai-metriques created
clusterrolebinding.rbac.authorization.k8s.io/essai-metriques created
comptable /metrics : yes
```

## 🧹 Clean-up

Delete the scratch namespace, then the RBAC objects that belong to no
namespace:

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

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-rbac-role-rolebinding
dsoxlab check ckad-rbac-role-rolebinding
```

```text
╭─ Result: ckad-rbac-role-rolebinding ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests     │
╰──────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a user who must be able to read the Pods of
a namespace and their logs, and nothing else.

```bash
dsoxlab run ckad-rbac-role-rolebinding
dsoxlab challenge ckad-rbac-role-rolebinding
```
