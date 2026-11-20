# Switch context and set the default namespace

kubectl can talk to several clusters. It finds their addresses and your
credentials in a file, `~/.kube/config`, called the **kubeconfig**. A
**context** is an entry of this file that says: this cluster, with this user,
and possibly this namespace. A **namespace** is a storage space inside a
cluster.

The lesson shows the `kubectl config` commands. This course makes you use
them on two clusters at once, and diagnose the errors they produce: a context
that points to an unknown cluster, a context name that changed, a kubeconfig
copied with the wrong permissions.

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
kubectl and clusters on `v1.37.0`) on 20 November 2026.

## 📚 Exercise 1: query the other cluster without switching context

The context in use is `kind-boutique`. The `--context` option targets another
context for a single command. Query the staging cluster, then check whether
the context in use changed:

```bash
kubectl config current-context
kubectl --context=recette get nodes
kubectl config current-context
```

```text
kind-boutique
NAME                STATUS   ROLES           AGE   VERSION
lab-control-plane   Ready    control-plane   63s   v1.37.0
kind-boutique
```

The node shown, `lab-control-plane`, belongs to the staging cluster. Yet the
context in use stays `kind-boutique`. `--context` does not change the
kubeconfig: it is the option to use in a script, which must not depend on the
state of the file.

## 📚 Exercise 2: see that `-n` wins over the context's namespace

Set `local-path-storage` as the default namespace of the context in use, then
list the Pods with and without `-n`:

```bash
kubectl config set-context --current --namespace=local-path-storage
kubectl get pods
kubectl get pods -n kube-system -o name | head -3
kubectl config view --minify -o jsonpath='{..namespace}'; echo
```

```text
Context "kind-boutique" modified.
NAME                                      READY   STATUS    RESTARTS   AGE
local-path-provisioner-75f7fc7dc5-h65dp   1/1     Running   0          15s
pod/coredns-559f6c778d-jwhr5
pod/coredns-559f6c778d-sz6ll
pod/etcd-boutique-control-plane
local-path-storage
```

Without `-n`, kubectl works in the context's namespace. With `-n`, it works in
the one you give, for that command only. The last line shows that the
context's namespace did not move.

## 📚 Exercise 3: create an object without saying where, then look for it

This is the challenge's move, on another cluster and another namespace.
Create a **ConfigMap**, a small object that stores settings, without
`--context` or `-n`, then ask where it is:

```bash
kubectl create configmap essai-ici --from-literal=origine=cours
kubectl get configmap essai-ici -o jsonpath='{.metadata.namespace}{"\n"}'
```

```text
configmap/essai-ici created
local-path-storage
```

It is in `local-path-storage`, the namespace of the context in use. Now look
for it on the other cluster, in the same namespace:

```bash
kubectl --context=recette get configmap essai-ici -n local-path-storage
```

```text
Error from server (NotFound): configmaps "essai-ici" not found
```

The staging cluster also has a `local-path-storage` namespace, but the
ConfigMap is not there. Two clusters share nothing: an object only exists on
the cluster where it was created. Set the `default` namespace back on your
context:

```bash
kubectl config set-context --current --namespace=default
```

```text
Context "kind-boutique" modified.
```

## 📚 Exercise 4: diagnose a context that points to an unknown cluster

A context ties a cluster and a user together by their names. Create one,
`casse`, with a typo in the cluster name (`kind-boutiqe`), and use it:

```bash
kubectl config set-context casse --cluster=kind-boutiqe --user=kind-boutique
kubectl --context=casse get nodes
```

```text title="Excerpt of the output"
Context "casse" created.
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

kubectl created the context without checking that the cluster exists. Then it
found no address for `kind-boutiqe` and fell back to `localhost:8080`, where
nothing listens. Several `memcache.go` lines come before this message and say
the same thing. The message does not name the typo: you find it by comparing
the names.

```bash
kubectl config get-clusters
kubectl config get-contexts casse
```

```text
NAME
kind-boutique
recette
CURRENT   NAME    CLUSTER        AUTHINFO        NAMESPACE
          casse   kind-boutiqe   kind-boutique
```

The `CLUSTER` column of the context names `kind-boutiqe`, missing from the
list of clusters. Delete this context:

```bash
kubectl config delete-context casse
```

```text
deleted context casse from /home/ansible/.kube/config
```

## 📚 Exercise 5: switch context in a single terminal

`kubectl config use-context` writes to `~/.kube/config`. The change therefore
applies to all your terminals. The `KUBECONFIG` variable points kubectl to
another file: a change made in that file does not touch the other terminals.
Work on a copy:

```bash
cp ~/.kube/config ~/essai-kubeconfig
chmod 600 ~/essai-kubeconfig
KUBECONFIG=~/essai-kubeconfig kubectl config use-context recette
KUBECONFIG=~/essai-kubeconfig kubectl config current-context
kubectl config current-context
```

```text
Switched to context "recette".
recette
kind-boutique
```

The copy uses `recette`. Your `~/.kube/config` still uses `kind-boutique`. In
a terminal where you run `export KUBECONFIG=~/essai-kubeconfig`, every later
kubectl command reads the copy, until the terminal closes.

## 📚 Exercise 6: rename a context

A context name shows up in your commands and your scripts. Rename `recette` in
the copy, then run a command that uses the old name:

```bash
KUBECONFIG=~/essai-kubeconfig kubectl config rename-context recette recette-essai
KUBECONFIG=~/essai-kubeconfig kubectl --context=recette get nodes
KUBECONFIG=~/essai-kubeconfig kubectl config get-contexts
```

```text
Context "recette" renamed to "recette-essai".
Error in configuration: context was not found for specified context: recette
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
          kind-boutique   kind-boutique   kind-boutique   default
*         recette-essai   recette         recette
```

Only the name of the context changed: it still points to the `recette`
cluster and the `recette` user, and it is still the context in use in the
copy. Any script that wrote `--context=recette` now fails. This
`context was not found` message is the one a typo gives: when you see it, list
the contexts. Delete the copy:

```bash
rm ~/essai-kubeconfig
```

## 📚 Exercise 7: see what really protects the kubeconfig

Look at the permissions of the file, and those of the two directories that
contain it:

```bash
ls -ld ~ ~/.kube ~/.kube/config
```

```text
drwx------ 15 ansible ansible  4096 Nov 20 07:02 /home/ansible
drwx------  3 ansible ansible  4096 Nov 20 07:02 /home/ansible/.kube
-rw-r--r--  1 ansible ansible 11119 Nov 20 07:02 /home/ansible/.kube/config
```

The file is `-rw-r--r--`: its permissions let any account read it. But both
directories are `drwx------`, and another account cannot go through them.
Check it with the `nobody` account, which has no particular right:

```bash
sudo -u nobody head -1 ~/.kube/config
```

```text
head: cannot open '/home/ansible/.kube/config' for reading: Permission denied
```

Today, the directories protect the file. That protection disappears as soon as
the file is copied somewhere else, because the copy keeps its permissions. Copy
it into `/tmp`, a directory every account can go through, and look for the
private keys there with the `nobody` account:

```bash
cp ~/.kube/config /tmp/essai-kubeconfig
ls -l /tmp/essai-kubeconfig
sudo -u nobody grep -c client-key-data /tmp/essai-kubeconfig
```

```text
-rw-r--r-- 1 ansible ansible 11119 Nov 20 07:02 /tmp/essai-kubeconfig
2
```

`nobody` reads the copy: it holds two private keys, one per cluster. With
them, anyone acts on both clusters with your rights. Fix the permissions of
the copy, then try again:

```bash
chmod 600 /tmp/essai-kubeconfig
sudo -u nobody grep -c client-key-data /tmp/essai-kubeconfig
rm /tmp/essai-kubeconfig
```

```text
grep: /tmp/essai-kubeconfig: Permission denied
```

With `-rw-------`, the file protects itself, wherever it is copied.

## 🧹 Clean up

First delete what you created during the exercises: the `essai-ici`
ConfigMap. The kubeconfig copies are already deleted.

```bash
kubectl delete configmap essai-ici -n local-path-storage
kubectl config get-contexts
```

```text
configmap "essai-ici" deleted from local-path-storage namespace
CURRENT   NAME            CLUSTER         AUTHINFO        NAMESPACE
*         kind-boutique   kind-boutique   kind-boutique   default
          recette         recette         recette
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
