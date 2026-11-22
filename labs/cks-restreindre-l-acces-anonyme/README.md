# Restrict anonymous access to the API server and the kubelet

The lesson shows how to query RBAC on behalf of the anonymous user, then how
the `Node` authorizer and the `NodeRestriction` admission bound a kubelet.
This course adds three cases it does not show: comparing what an anonymous
client and an authenticated user get, finding a right given to **every**
authenticated user, and watching the `Node` authorizer decide Secret by
Secret.

You work on the kubeadm cluster, with a test namespace and a test binding. The
challenge targets the authentication configuration of the API server, the
kubelet of the control plane and the anonymous bindings of the cluster: you
will do it on your own, at the end.

Related page: [Restrict access to the API server](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/restreindre-acces-api-server/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-restreindre-l-acces-anonyme
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl has administrator rights, and `ssh` reaches
the workers.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2.

## ⚖️ Exercise 1: an anonymous client and an authenticated one, path by path

A `SubjectAccessReview` asks the API server whether an identity would be
allowed to act, without creating anything. Ask the same question for four
paths, first on behalf of the anonymous group (`system:unauthenticated`), then
on behalf of the group of any authenticated client (`system:authenticated`):

```bash
for g in system:unauthenticated system:authenticated; do for u in /version /healthz /apis /metrics; do printf '%-24s %-9s ' $g $u; echo '{"apiVersion":"authorization.k8s.io/v1","kind":"SubjectAccessReview","spec":{"user":"essai","groups":["'$g'"],"nonResourceAttributes":{"verb":"get","path":"'$u'"}}}' | kubectl create -f - -o jsonpath='{.status.allowed}{"\n"}'; done; done
```

```text
system:unauthenticated   /version  true
system:unauthenticated   /healthz  true
system:unauthenticated   /apis     false
system:unauthenticated   /metrics  false
system:authenticated     /version  true
system:authenticated     /healthz  true
system:authenticated     /apis     true
system:authenticated     /metrics  false
```

Both groups read `/version` and `/healthz`: that is the default binding
`system:public-info-viewer`. Only an authenticated client reads `/apis`, the
list of the cluster APIs (binding `system:discovery`). Neither reads
`/metrics`. A single command gives you the map of what each group gets before
any role of its own.

## 🚪 Exercise 2: a right given to every authenticated user

People think of the anonymous user and forget the other broad group:
`system:authenticated` holds **every** identity the API server recognises,
including a service account from any namespace. Give it the `view` role, then
ask whether an unknown authenticated user would read the Pods of
`kube-system`:

```bash
kubectl create clusterrolebinding essai-ouvert --clusterrole=view --group=system:authenticated; printf 'un inconnu authentifié lit les pods de kube-system : '; kubectl auth can-i list pods -n kube-system --as=quiconque --as-group=system:authenticated
```

```text
clusterrolebinding.rbac.authorization.k8s.io/essai-ouvert created
un inconnu authentifié lit les pods de kube-system : yes
```

`yes`: any account of the cluster now reads the whole cluster. Find the
bindings that target this group:

```bash
kubectl get clusterrolebindings -o jsonpath='{range .items[*]}{.metadata.name}{" "}{range .subjects[*]}{.name}{" "}{end}{"\n"}{end}' | grep -E ' system:authenticated '
```

```text
calico-tiered-policy-passthrough system:authenticated 
essai-ouvert system:authenticated 
system:basic-user system:authenticated 
system:discovery system:authenticated 
system:public-info-viewer system:authenticated system:unauthenticated 
```

The `system:` bindings and the Calico one come from the installation.
`essai-ouvert` is yours: this is how you spot a binding added by hand, by
comparing it to the starting list. Remove it:

```bash
kubectl delete clusterrolebinding essai-ouvert
```

```text
clusterrolebinding.rbac.authorization.k8s.io "essai-ouvert" deleted
```

## 🔗 Exercise 3: a kubelet only reads the Secrets of its Pods

The `Node` authorizer does not let a kubelet read "the Secrets of its node" in
general: it follows a graph. A kubelet reads a Secret only if a Pod scheduled
on **its** node uses it. Create a test namespace and two Secrets:

```bash
kubectl create namespace essai-graphe; kubectl -n essai-graphe create secret generic essai-monte --from-literal=cle=1; kubectl -n essai-graphe create secret generic essai-libre --from-literal=cle=2
```

```text
namespace/essai-graphe created
secret/essai-monte created
secret/essai-libre created
```

Start on `k8s-w1.lab` a Pod that mounts only `essai-monte`:

```bash
kubectl -n essai-graphe run lecteur --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e --overrides='{"spec":{"nodeName":"k8s-w1.lab","volumes":[{"name":"s","secret":{"secretName":"essai-monte"}}],"containers":[{"name":"lecteur","image":"busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e","command":["sleep","3600"],"volumeMounts":[{"name":"s","mountPath":"/s"}]}]}}'; kubectl -n essai-graphe wait --for=condition=Ready pod/lecteur --timeout=90s
```

```text
pod/lecteur created
pod/lecteur condition met
```

Now ask, with the identity of the kubelet of `k8s-w1.lab`, whether it would
read each of the two Secrets:

```bash
for s in essai-monte essai-libre; do printf 'kubelet de k8s-w1, secret %-12s : ' $s; ssh -o StrictHostKeyChecking=no k8s-w1.lab sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf auth can-i get secret/$s -n essai-graphe; done
```

```text
kubelet de k8s-w1, secret essai-monte  : yes
kubelet de k8s-w1, secret essai-libre  : no - node: no relationship found between node 'k8s-w1.lab' and this object
```

It reads `essai-monte`, which its Pod uses. It does not read `essai-libre`,
although it sits in the same namespace: `no relationship found`. Ask the same
question with the kubelet of the control plane:

```bash
printf 'kubelet de k8s-cp, secret essai-monte  : '; sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf auth can-i get secret/essai-monte -n essai-graphe
```

```text
kubelet de k8s-cp, secret essai-monte  : no - node: no relationship found between node 'k8s-cp.lab' and this object
```

Refused as well: no Pod of `k8s-cp.lab` mounts that Secret. A compromised node
therefore only reads the Secrets of the Pods it already hosts, not those of
the rest of the cluster.

## 🧹 Clean-up

Delete the test namespace, which removes the Pod and both Secrets, and check
the test binding no longer exists:

```bash
kubectl delete namespace essai-graphe --wait=true --timeout=120s; kubectl get clusterrolebinding essai-ouvert 2>&1 | tail -1
```

```text
namespace "essai-graphe" deleted
Error from server (NotFound): clusterrolebindings.rbac.authorization.k8s.io "essai-ouvert" not found
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-restreindre-l-acces-anonyme
dsoxlab check cks-restreindre-l-acces-anonyme
```

```text
╭─ Result: cks-restreindre-l-acces-anonyme ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests          │
╰───────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an API server that answers clients with no
credentials, a binding that opens the cluster to them, and a kubelet that
accepts everybody.

```bash
dsoxlab run cks-restreindre-l-acces-anonyme
dsoxlab challenge cks-restreindre-l-acces-anonyme
```
