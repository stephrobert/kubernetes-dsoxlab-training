# Switch context and set the default namespace

kubectl can talk to several clusters. It finds their addresses and your
credentials in a file, `~/.kube/config`, called the **kubeconfig**. A
**context** is an entry of this file that says: this cluster, with this user,
and possibly this namespace. A **namespace** is a storage space inside a
cluster.

In this course, you redo the moves of the lesson: see which context is in use,
target another one for a single command, set the default namespace, create and
delete a context, create an object in the right place, and protect a
kubeconfig.

You work on the `kind-boutique` context and on scratch objects. The challenge
will ask you to switch to `recette`: you will do it on your own, at the end.

Related page: [kubeconfig and kubectl contexts](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubeconfig-and-contexts/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-changer-de-contexte
```

You are now connected to the `k8s-kind.lab` machine. Two clusters are running
there. Your kubeconfig knows two contexts: `kind-boutique`, in use right now,
and `recette`.

The outputs shown in this course were recorded on this machine (Debian 13.7,
kubectl and clusters on `v1.37.0`) on 19 November 2026.

## 📚 Exercise 1: see which context is in use

Before changing anything, look at which cluster you target. List the contexts,
then show only the one in use:

```bash
kubectl config get-contexts
kubectl config current-context
```

```text
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique
          recette         recette         recette
kind-boutique
```

The asterisk shows the context in use: `kind-boutique`. The `NAMESPACE` column
is empty: no namespace is set, so kubectl works in the `default` namespace. You
can check it like this:

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo
```

The command shows an empty line: no namespace is set.

## 📚 Exercise 2: target another namespace for a single command

List the Pods with no option, then in the `local-path-storage` namespace:

```bash
kubectl get pods
kubectl get pods -n local-path-storage
```

```text
No resources found in default namespace.
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          33s
```

The `default` namespace is empty. The `-n` option targets another namespace,
for this command only: it changes nothing in the kubeconfig.

## 📚 Exercise 3: target another context for a single command

The `--context` option does the same for the context: it applies to a single
command, without changing the context in use. It is the right way to do it in
a script.

```bash
kubectl --context=kind-boutique get nodes
```

```text
NAME                     STATUS   ROLES           AGE   VERSION
boutique-control-plane   Ready    control-plane   43s   v1.37.0
```

Now type a context name that does not exist, in two ways:

```bash
kubectl --context=xxx get nodes
kubectl config use-context xxx
kubectl config current-context
```

```text
Error in configuration: context was not found for specified context: xxx
error: no context exists with the name: "xxx"
kind-boutique
```

Both commands refuse the name, each with its own message: learn to recognise
them. The context in use did not change.

## 📚 Exercise 4: set the default namespace

If you work for a long time in the same namespace, set it on the context in
use. You will no longer need to type `-n`:

```bash
kubectl config set-context --current --namespace=local-path-storage
kubectl config view --minify -o jsonpath='{..namespace}'; echo
kubectl get pods
```

```text
Context "kind-boutique" modified.
local-path-storage
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          33s
```

Without `-n`, `kubectl get pods` now lists the namespace you set.

Watch out for a trap: kubectl does not check that the namespace exists. Make a
typo on purpose:

```bash
kubectl config set-context --current --namespace=local-path-storag
kubectl get pods
kubectl config get-contexts
```

```text
Context "kind-boutique" modified.
No resources found in local-path-storag namespace.
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique   local-path-storag
          recette         recette         recette
```

kubectl accepts the mistyped name without a word, and the next command answers
as if the namespace were empty. If an object seems to have disappeared, look at
the `NAMESPACE` column first: here, it shows the typo.

## 📚 Exercise 5: create a context, use it, then delete it

Create a `boutique-stockage` context. It targets the same cluster as
`kind-boutique`, with the same user, but directly in the `local-path-storage`
namespace. Switch to it, then come back:

```bash
kubectl config set-context boutique-stockage \
  --cluster=kind-boutique --user=kind-boutique --namespace=local-path-storage
kubectl config use-context boutique-stockage
kubectl get pods
kubectl config use-context kind-boutique
```

```text
Context "boutique-stockage" created.
Switched to context "boutique-stockage".
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          34s
Switched to context "kind-boutique".
```

`use-context` saves the change in the kubeconfig. It therefore applies to all
your terminals at once. Then delete the scratch context:

```bash
kubectl config delete-context boutique-stockage
kubectl config get-contexts
```

```text
deleted context boutique-stockage from /home/ansible/.kube/config
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique   local-path-storag
          recette         recette         recette
```

Deleting a context deletes neither the cluster nor the user: only the entry.
Notice that `kind-boutique` still carries the typo of exercise 4: you fix it
in the next exercise.

## 📚 Exercise 6: create an object in the right place

Set the `default` namespace back on the context in use. Then create a
**ConfigMap**, a small object that stores settings, without giving any context
or namespace:

```bash
kubectl config set-context --current --namespace=default
kubectl create configmap essai --from-literal=origine=cours
```

```text
Context "kind-boutique" modified.
configmap/essai created
```

Look for where it was created:

```bash
kubectl get configmap essai -n default
kubectl get configmap essai -n local-path-storage
```

```text
NAME    DATA   AGE
essai   1      0s
Error from server (NotFound): configmaps "essai" not found
```

With no option, kubectl creates the object in the context in use and in its
default namespace, and nowhere else. That is why you check the context before
acting.

## 📚 Exercise 7: protect a kubeconfig

A kubeconfig holds what it takes to act on the cluster with your rights. Look
at which identity it gives you:

```bash
kubectl auth whoami
```

```text
ATTRIBUTE                                           VALUE
Username                                            kubernetes-admin
Groups                                              [kubeadm:cluster-admins system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=8cf552b482997b7b400d7673cd364a6bdb0ef0046946c01837da00bc5cbd3b8e]
```

The `kubeadm:cluster-admins` group grants every right on the cluster. This file
is therefore protected like a password: only you must be able to read it.
Practise on a copy:

```bash
cp ~/.kube/config ~/essai-kubeconfig
ls -l ~/essai-kubeconfig
chmod 600 ~/essai-kubeconfig
ls -l ~/essai-kubeconfig
```

```text
-rw-r--r-- 1 ansible ansible 11119 Nov 19 09:50 /home/ansible/essai-kubeconfig
-rw------- 1 ansible ansible 11119 Nov 19 09:50 /home/ansible/essai-kubeconfig
```

Before, `-rw-r--r--`: every account on the machine could read the file. After
`chmod 600`, `-rw-------`: only you can read and modify it.

## 🧹 Clean up

First delete what you created during the exercises: the `essai` ConfigMap and the kubeconfig copy.

```bash
kubectl delete configmap essai
rm ~/essai-kubeconfig
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-changer-de-contexte
dsoxlab check k8s-changer-de-contexte
```

```text
╭─ Result: k8s-changer-de-contexte ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you, untouched.

## 🎯 The challenge

Your turn, on your own this time: switch to the recette cluster, set the right
namespace there, create the requested ConfigMap there, and protect your
kubeconfig.

```bash
dsoxlab run k8s-changer-de-contexte
dsoxlab challenge k8s-changer-de-contexte
```
