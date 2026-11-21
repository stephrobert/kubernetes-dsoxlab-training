# Retirer cluster-admin à un compte de service, sans le priver de son travail

La leçon montre RBAC et le principe du moindre privilège : ne donner que les
droits utiles. Ce cours vous fait auditer des droits plutôt que les écrire, et
ajoute des cas que la leçon ne montre pas : retrouver qui détient
`cluster-admin`, un droit donné à tous les comptes de service d'un namespace,
la différence entre `view` et `edit` pour les Secrets, et les jokers face aux
sous-ressources comme `pods/exec`.

Vous travaillez dans un namespace d'essai, `essai-moindre`, avec deux comptes
de service, `outil` et `stagiaire`, et un Secret `coffre`. Le challenge porte
sur un autre compte et un autre namespace : vous le ferez seul, à la fin.

Page associée : [RBAC](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/rbac/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-rbac-least-privilege
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, avec les droits
d'administrateur.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Les droits d'un compte de service se testent avec `kubectl auth can-i` et
`--as=system:serviceaccount:<namespace>:<nom>`. Créez le namespace, les deux
comptes, le Secret, et un raccourci dangereux : `cluster-admin` donné à
`outil` pour tout le cluster.

```bash
kubectl create namespace essai-moindre; kubectl create serviceaccount outil -n essai-moindre; kubectl create serviceaccount stagiaire -n essai-moindre; kubectl create secret generic coffre -n essai-moindre --from-literal=cle=essai; kubectl create clusterrolebinding essai-raccourci --clusterrole=cluster-admin --serviceaccount=essai-moindre:outil
```

```text
namespace/essai-moindre created
serviceaccount/outil created
serviceaccount/stagiaire created
secret/coffre created
clusterrolebinding.rbac.authorization.k8s.io/essai-raccourci created
```

## 👑 Exercice 1 : qui détient cluster-admin ?

Listez les ClusterRoleBindings qui donnent `cluster-admin`, avec leurs
bénéficiaires :

```bash
kubectl get clusterrolebindings -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.metadata.name}: {range .subjects[*]}{.kind}/{.namespace}/{.name} {end}{"\n"}{end}'
```

```text
cluster-admin: Group//system:masters 
dev-admin-binding: ServiceAccount/equipe-dev/dev-sa 
essai-raccourci: ServiceAccount/essai-moindre/outil 
kubeadm:cluster-admins: Group//kubeadm:cluster-admins 
```

Deux liaisons sont livrées par kubeadm, vers des groupes d'administrateurs.
`essai-raccourci` est le vôtre. `dev-admin-binding` appartient au challenge :
laissez-le pour plus tard. `cluster-admin` peut aussi être donné dans un seul
namespace, par un RoleBinding. Vérifiez qu'il n'y en a pas :

```bash
kubectl get rolebindings -A -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'; echo "(fin des RoleBindings vers cluster-admin)"
```

```text
(fin des RoleBindings vers cluster-admin)
```

Aucun. Supprimez le raccourci et vérifiez que `outil` ne peut plus tout
faire :

```bash
kubectl delete clusterrolebinding essai-raccourci; printf 'outil peut tout ? '; kubectl auth can-i '*' '*' --as=system:serviceaccount:essai-moindre:outil
```

```text
clusterrolebinding.rbac.authorization.k8s.io "essai-raccourci" deleted
outil peut tout ? no
```

## 👥 Exercice 2 : un droit donné à tous les comptes d'un namespace

Chaque compte de service appartient au groupe
`system:serviceaccounts:<namespace>`. Donnez `view` à ce groupe :

```bash
kubectl create rolebinding tous-lisent -n essai-moindre --clusterrole=view --group=system:serviceaccounts:essai-moindre; for s in outil stagiaire; do printf '%s list pods : ' $s; kubectl auth can-i list pods -n essai-moindre --as=system:serviceaccount:essai-moindre:$s; done
```

```text
rolebinding.rbac.authorization.k8s.io/tous-lisent created
outil list pods : yes
stagiaire list pods : yes
```

Les deux comptes lisent les Pods. Créez maintenant un nouveau compte :

```bash
kubectl create serviceaccount nouveau -n essai-moindre; printf 'nouveau list pods : '; kubectl auth can-i list pods -n essai-moindre --as=system:serviceaccount:essai-moindre:nouveau
```

```text
serviceaccount/nouveau created
nouveau list pods : yes
```

Le compte créé après la liaison a déjà le droit. Donner un droit au groupe,
c'est le donner à tout compte qui sera créé un jour dans ce namespace, y
compris par quelqu'un d'autre. Retirez cette liaison :

```bash
kubectl delete rolebinding tous-lisent -n essai-moindre
```

```text
rolebinding.rbac.authorization.k8s.io "tous-lisent" deleted from essai-moindre namespace
```

## 🔐 Exercice 3 : view et edit face aux Secrets

Donnez `view` à `stagiaire`, et testez la lecture du Secret :

```bash
kubectl create rolebinding stagiaire-view -n essai-moindre --clusterrole=view --serviceaccount=essai-moindre:stagiaire; printf 'view, get secret : '; kubectl auth can-i get secret/coffre -n essai-moindre --as=system:serviceaccount:essai-moindre:stagiaire
```

```text
rolebinding.rbac.authorization.k8s.io/stagiaire-view created
view, get secret : no
```

Refusé : `view` exclut volontairement les Secrets. Remplacez par `edit` :

```bash
kubectl delete rolebinding stagiaire-view -n essai-moindre; kubectl create rolebinding stagiaire-edit -n essai-moindre --clusterrole=edit --serviceaccount=essai-moindre:stagiaire; printf 'edit, get secret : '; kubectl auth can-i get secret/coffre -n essai-moindre --as=system:serviceaccount:essai-moindre:stagiaire
```

```text
rolebinding.rbac.authorization.k8s.io "stagiaire-view" deleted from essai-moindre namespace
rolebinding.rbac.authorization.k8s.io/stagiaire-edit created
edit, get secret : yes
```

`edit` lit les Secrets. Donner `edit` pour qu'un compte puisse modifier des
Deployments lui ouvre donc aussi les mots de passe du namespace. Retirez
cette liaison :

```bash
kubectl delete rolebinding stagiaire-edit -n essai-moindre
```

```text
rolebinding.rbac.authorization.k8s.io "stagiaire-edit" deleted from essai-moindre namespace
```

## 🃏 Exercice 4 : les jokers et les sous-ressources

`kubectl exec` passe par la sous-ressource `pods/exec`. Le test se fait avec
`--subresource=exec` : écrire `pods/exec` serait lu comme un Pod nommé `exec`.
Donnez à `outil` les droits courants sur les Pods :

```bash
kubectl create role pods-precis -n essai-moindre --verb=get,list,create --resource=pods; kubectl create rolebinding outil-precis -n essai-moindre --role=pods-precis --serviceaccount=essai-moindre:outil; printf 'exec, avec pods : '; kubectl auth can-i create pods --subresource=exec -n essai-moindre --as=system:serviceaccount:essai-moindre:outil
```

```text
role.rbac.authorization.k8s.io/pods-precis created
rolebinding.rbac.authorization.k8s.io/outil-precis created
exec, avec pods : no
```

Pas d'`exec` : un droit sur `pods` ne couvre pas ses sous-ressources. Essayez
un joker sur les sous-ressources, `pods/*` :

```bash
kubectl create role pods-joker -n essai-moindre --verb='*' --resource='pods/*'; kubectl create rolebinding outil-joker -n essai-moindre --role=pods-joker --serviceaccount=essai-moindre:outil; printf 'exec, avec pods/* : '; kubectl auth can-i create pods --subresource=exec -n essai-moindre --as=system:serviceaccount:essai-moindre:outil
```

```text
role.rbac.authorization.k8s.io/pods-joker created
rolebinding.rbac.authorization.k8s.io/outil-joker created
exec, avec pods/* : no
```

Toujours non. RBAC n'accepte pas `pods/*` comme « toutes les sous-ressources
des Pods » : la règle est acceptée par l'API, mais elle ne donne rien. Une
sous-ressource s'écrit en entier (`pods/exec`). Essayez le joker complet,
`*` :

```bash
kubectl create role tout -n essai-moindre --verb='*' --resource='*'; kubectl create rolebinding outil-tout -n essai-moindre --role=tout --serviceaccount=essai-moindre:outil; printf 'exec, avec * : '; kubectl auth can-i create pods --subresource=exec -n essai-moindre --as=system:serviceaccount:essai-moindre:outil; printf 'get secret, avec * : '; kubectl auth can-i get secret/coffre -n essai-moindre --as=system:serviceaccount:essai-moindre:outil
```

```text
role.rbac.authorization.k8s.io/tout created
rolebinding.rbac.authorization.k8s.io/outil-tout created
exec, avec * : yes
get secret, avec * : yes
```

`*` ouvre tout, sous-ressources et Secrets compris. Relisez la liste des droits
de `outil` :

```bash
kubectl auth can-i --list -n essai-moindre --as=system:serviceaccount:essai-moindre:outil | head -6
```

```text
Resources                                       Non-Resource URLs                      Resource Names   Verbs
*                                               []                                     []               [*]
pods/*                                          []                                     []               [*]
selfsubjectreviews.authentication.k8s.io        []                                     []               [create]
selfsubjectaccessreviews.authorization.k8s.io   []                                     []               [create]
selfsubjectrulesreviews.authorization.k8s.io    []                                     []               [create]
```

La règle `pods/*` apparaît, alors qu'elle n'a aucun effet. Une liste de droits
se lit donc en connaissant ces règles : `*` est le vrai danger, `pods/*` une
fausse sécurité.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-moindre; kubectl delete clusterrolebinding essai-raccourci --ignore-not-found
```

```text
namespace "essai-moindre" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-rbac-least-privilege
dsoxlab check cks-rbac-least-privilege
```

```text
╭─ Résultat : cks-rbac-least-privilege ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un compte de service administrateur du cluster, à
ramener aux seuls droits dont il a besoin.

```bash
dsoxlab run cks-rbac-least-privilege
dsoxlab challenge cks-rbac-least-privilege
```
