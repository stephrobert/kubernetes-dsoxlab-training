# Switch context and set the default namespace

This course has you practise, on the lab machine, every move of the lesson:
read the active context, target another namespace or another context for a
single command, set the default namespace, create and delete a context, create
an object where the context says, and protect a kubeconfig. You work on the
`kind-boutique` context and on scratch objects: switching to `recette` is the
challenge, it is left for the end.

Related page: [kubeconfig and kubectl contexts](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubeconfig-and-contexts/).

## 🔧 Before you start

```bash
dsoxlab run k8s-changer-de-contexte
```

The command prepares the `k8s-kind.lab` machine and connects you to it. Two
kind clusters are running, and your `~/.kube/config` knows two contexts:
`kind-boutique`, active, and `recette`. The outputs below were recorded on
this machine (Debian 13.7, kubectl and clusters on `v1.37.0`) on 19 November
2026.

## 📚 Exercise 1: read where you are

Before any command that changes something, check which cluster you target.
List the contexts, then ask for the name of the active one only.

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

The asterisk marks the active context, `kind-boutique`. The `NAMESPACE`
column is empty for both contexts: with nothing set, kubectl works in
`default`. Check it on the current context only:

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo
```

The output is an empty line: no namespace is set.

## 📚 Exercise 2: change namespace for a single command

List the Pods with no option, then in the `local-path-storage` namespace.

```bash
kubectl get pods
kubectl get pods -n local-path-storage
```

```text
No resources found in default namespace.
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-75hhh   1/1     Running   0          33s
```

The first command queries `default`, which is empty. The second targets
another namespace for itself only: the `-n` option changes nothing in the
file.

## 📚 Exercise 3: target a context for a single command

`--context` does for the context what `-n` does for the namespace: it applies
to one command, without touching the active context. It is the form to use in
a script.

```bash
kubectl --context=kind-boutique get nodes
```

```text
NAME                     STATUS   ROLES           AGE   VERSION
boutique-control-plane   Ready    control-plane   43s   v1.37.0
```

Now type a context name that does not exist, in both forms:

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

Both forms refuse the name, with a different message: learn to recognise them.
The active context did not move.

## 📚 Exercise 4: set the default namespace of the current context

When you spend time in the same namespace, set it on the active context rather
than repeating `-n`.

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

`kubectl get pods`, with no `-n`, now lists the namespace you set. See the
trap: kubectl does not check that the namespace exists. Make a typo on
purpose:

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

The typo is accepted without a word, and the next command answers as if the
namespace were empty. When a resource seems to have disappeared, look at the
`NAMESPACE` column first: here it shows the mistyped name.

## 📚 Exercise 5: create a context, switch, come back, delete it

A context is just a name set on a cluster, a user and a namespace. Create
`boutique-stockage`, on the same cluster as `kind-boutique`, directly in
`local-path-storage`. Switch to it, then come back.

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

`use-context` rewrites `current-context` in the file: the switch applies to all
your terminals. Now delete the scratch context:

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

Deleting a context only deletes that shortcut: the cluster and the user stay in
the file. And `kind-boutique` still carries the mistyped namespace of the
previous exercise: you fix it in the next one.

## 📚 Exercise 6: create an object where the context says

Set the `default` namespace back on the current context, then create a
ConfigMap without naming any context or namespace.

```bash
kubectl config set-context --current --namespace=default
kubectl create configmap essai --from-literal=origine=cours
```

```text
Context "kind-boutique" modified.
configmap/essai created
```

Now look for where it landed:

```bash
kubectl get configmap essai -n default
kubectl get configmap essai -n local-path-storage
```

```text
NAME    DATA   AGE
essai   1      0s
Error from server (NotFound): configmaps "essai" not found
```

A command with no option creates the object in the active context and in its
default namespace, and nowhere else. That is why you check the context before
acting.

## 📚 Exercise 7: protect a kubeconfig

A kubeconfig holds what it takes to act on the cluster with your rights. Look
at the identity it carries:

```bash
kubectl auth whoami
```

```text
ATTRIBUTE                                           VALUE
Username                                            kubernetes-admin
Groups                                              [kubeadm:cluster-admins system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=8cf552b482997b7b400d7673cd364a6bdb0ef0046946c01837da00bc5cbd3b8e]
```

The `kubeadm:cluster-admins` group grants every right on the cluster. Such a
file is protected like an SSH key. Practise on a copy:

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

Before, `-rw-r--r--`: every account on the machine could read it. After,
`-rw-------`: read and write for you, nothing for the others.

## 🧹 Clean up

Remove what the exercises set up and put the context back as you found it:

```bash
kubectl delete configmap essai
kubectl config unset contexts.kind-boutique.namespace
rm ~/essai-kubeconfig
kubectl config get-contexts
```

```text
configmap "essai" deleted from default namespace
Property "contexts.kind-boutique.namespace" unset.
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique
          recette         recette         recette
```

`unset` removes the namespace from the context: the column is empty again, as
at the start. Leave the session and check:

```bash
exit
dsoxlab check k8s-changer-de-contexte
```

```text
╭─ Result: k8s-changer-de-contexte ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

Zero out of four: the machine is back to the starting state of the challenge.

## 🎯 The challenge

Now do the challenge on your own: move to the recette cluster, set the right
namespace there, create the proof there, and protect your kubeconfig.

```bash
dsoxlab run k8s-changer-de-contexte
dsoxlab challenge k8s-changer-de-contexte
```
