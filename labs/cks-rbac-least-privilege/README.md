# Take cluster-admin away from a service account, without stopping its work

The lesson shows RBAC and the principle of least privilege: give only the
rights that are needed. This course has you audit rights rather than write
them, and adds cases the lesson does not show: finding who holds
`cluster-admin`, a right given to every service account of a namespace, the
difference between `view` and `edit` for Secrets, and wildcards against
subresources such as `pods/exec`.

You work in a scratch namespace, `essai-moindre`, with two service accounts,
`outil` and `stagiaire` ("tool" and "intern"), and a `coffre` ("safe")
Secret. The challenge is about another account and another namespace: you
will do it on your own, at the end.

Related page: [RBAC](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/rbac/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-rbac-least-privilege
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, with administrator
rights.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

A service account's rights are tested with `kubectl auth can-i` and
`--as=system:serviceaccount:<namespace>:<name>`. Create the namespace, the
two accounts, the Secret, and a dangerous shortcut: `cluster-admin` given to
`outil` for the whole cluster.

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

## 👑 Exercise 1: who holds cluster-admin?

List the ClusterRoleBindings that grant `cluster-admin`, with their subjects:

```bash
kubectl get clusterrolebindings -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.metadata.name}: {range .subjects[*]}{.kind}/{.namespace}/{.name} {end}{"\n"}{end}'
```

```text
cluster-admin: Group//system:masters 
dev-admin-binding: ServiceAccount/equipe-dev/dev-sa 
essai-raccourci: ServiceAccount/essai-moindre/outil 
kubeadm:cluster-admins: Group//kubeadm:cluster-admins 
```

Two bindings are shipped by kubeadm, to administrator groups.
`essai-raccourci` ("shortcut") is yours. `dev-admin-binding` belongs to the
challenge: leave it for later. `cluster-admin` can also be granted in a single
namespace, through a RoleBinding. Check there is none:

```bash
kubectl get rolebindings -A -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'; echo "(fin des RoleBindings vers cluster-admin)"
```

```text
(fin des RoleBindings vers cluster-admin)
```

None. Delete the shortcut and check that `outil` can no longer do everything:

```bash
kubectl delete clusterrolebinding essai-raccourci; printf 'outil peut tout ? '; kubectl auth can-i '*' '*' --as=system:serviceaccount:essai-moindre:outil
```

```text
clusterrolebinding.rbac.authorization.k8s.io "essai-raccourci" deleted
outil peut tout ? no
```

## 👥 Exercise 2: a right given to every account of a namespace

Every service account belongs to the `system:serviceaccounts:<namespace>`
group. Give `view` to that group:

```bash
kubectl create rolebinding tous-lisent -n essai-moindre --clusterrole=view --group=system:serviceaccounts:essai-moindre; for s in outil stagiaire; do printf '%s list pods : ' $s; kubectl auth can-i list pods -n essai-moindre --as=system:serviceaccount:essai-moindre:$s; done
```

```text
rolebinding.rbac.authorization.k8s.io/tous-lisent created
outil list pods : yes
stagiaire list pods : yes
```

Both accounts read Pods. Now create a new account:

```bash
kubectl create serviceaccount nouveau -n essai-moindre; printf 'nouveau list pods : '; kubectl auth can-i list pods -n essai-moindre --as=system:serviceaccount:essai-moindre:nouveau
```

```text
serviceaccount/nouveau created
nouveau list pods : yes
```

The account created after the binding already has the right. Giving a right
to the group means giving it to any account that will ever be created in this
namespace, including by someone else. Remove this binding:

```bash
kubectl delete rolebinding tous-lisent -n essai-moindre
```

```text
rolebinding.rbac.authorization.k8s.io "tous-lisent" deleted from essai-moindre namespace
```

## 🔐 Exercise 3: view and edit against Secrets

Give `view` to `stagiaire`, and test reading the Secret:

```bash
kubectl create rolebinding stagiaire-view -n essai-moindre --clusterrole=view --serviceaccount=essai-moindre:stagiaire; printf 'view, get secret : '; kubectl auth can-i get secret/coffre -n essai-moindre --as=system:serviceaccount:essai-moindre:stagiaire
```

```text
rolebinding.rbac.authorization.k8s.io/stagiaire-view created
view, get secret : no
```

Refused: `view` deliberately leaves Secrets out. Replace it with `edit`:

```bash
kubectl delete rolebinding stagiaire-view -n essai-moindre; kubectl create rolebinding stagiaire-edit -n essai-moindre --clusterrole=edit --serviceaccount=essai-moindre:stagiaire; printf 'edit, get secret : '; kubectl auth can-i get secret/coffre -n essai-moindre --as=system:serviceaccount:essai-moindre:stagiaire
```

```text
rolebinding.rbac.authorization.k8s.io "stagiaire-view" deleted from essai-moindre namespace
rolebinding.rbac.authorization.k8s.io/stagiaire-edit created
edit, get secret : yes
```

`edit` reads Secrets. Giving `edit` so that an account can change Deployments
therefore also opens the namespace's passwords to it. Remove this binding:

```bash
kubectl delete rolebinding stagiaire-edit -n essai-moindre
```

```text
rolebinding.rbac.authorization.k8s.io "stagiaire-edit" deleted from essai-moindre namespace
```

## 🃏 Exercise 4: wildcards and subresources

`kubectl exec` goes through the `pods/exec` subresource. The test uses
`--subresource=exec`: writing `pods/exec` would be read as a Pod named `exec`.
Give `outil` the usual rights on Pods:

```bash
kubectl create role pods-precis -n essai-moindre --verb=get,list,create --resource=pods; kubectl create rolebinding outil-precis -n essai-moindre --role=pods-precis --serviceaccount=essai-moindre:outil; printf 'exec, avec pods : '; kubectl auth can-i create pods --subresource=exec -n essai-moindre --as=system:serviceaccount:essai-moindre:outil
```

```text
role.rbac.authorization.k8s.io/pods-precis created
rolebinding.rbac.authorization.k8s.io/outil-precis created
exec, avec pods : no
```

No `exec`: a right on `pods` does not cover its subresources. Try a wildcard on
subresources, `pods/*`:

```bash
kubectl create role pods-joker -n essai-moindre --verb='*' --resource='pods/*'; kubectl create rolebinding outil-joker -n essai-moindre --role=pods-joker --serviceaccount=essai-moindre:outil; printf 'exec, avec pods/* : '; kubectl auth can-i create pods --subresource=exec -n essai-moindre --as=system:serviceaccount:essai-moindre:outil
```

```text
role.rbac.authorization.k8s.io/pods-joker created
rolebinding.rbac.authorization.k8s.io/outil-joker created
exec, avec pods/* : no
```

Still no. RBAC does not accept `pods/*` as "every subresource of Pods": the
API accepts the rule, but it grants nothing. A subresource is written in full
(`pods/exec`). Try the full wildcard, `*`:

```bash
kubectl create role tout -n essai-moindre --verb='*' --resource='*'; kubectl create rolebinding outil-tout -n essai-moindre --role=tout --serviceaccount=essai-moindre:outil; printf 'exec, avec * : '; kubectl auth can-i create pods --subresource=exec -n essai-moindre --as=system:serviceaccount:essai-moindre:outil; printf 'get secret, avec * : '; kubectl auth can-i get secret/coffre -n essai-moindre --as=system:serviceaccount:essai-moindre:outil
```

```text
role.rbac.authorization.k8s.io/tout created
rolebinding.rbac.authorization.k8s.io/outil-tout created
exec, avec * : yes
get secret, avec * : yes
```

`*` opens everything, subresources and Secrets included. Read `outil`'s list
of rights again:

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

The `pods/*` rule shows up, although it has no effect. A list of rights must
therefore be read knowing these rules: `*` is the real danger, `pods/*` a
false sense of security.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-moindre; kubectl delete clusterrolebinding essai-raccourci --ignore-not-found
```

```text
namespace "essai-moindre" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-rbac-least-privilege
dsoxlab check cks-rbac-least-privilege
```

```text
╭─ Result: cks-rbac-least-privilege ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests   │
╰────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a service account that is a cluster
administrator, to bring back to only the rights it needs.

```bash
dsoxlab run cks-rbac-least-privilege
dsoxlab challenge cks-rbac-least-privilege
```
