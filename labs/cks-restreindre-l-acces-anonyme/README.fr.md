# Restreindre l'accès anonyme à l'API server et au kubelet

La leçon montre comment interroger le RBAC au nom de l'utilisateur anonyme,
puis comment l'autorisation `Node` et l'admission `NodeRestriction` bornent un
kubelet. Ce cours ajoute trois cas qu'elle ne montre pas : comparer ce
qu'obtiennent un anonyme et un utilisateur authentifié, retrouver un droit
donné à **tous** les utilisateurs authentifiés, et voir l'autorisation `Node`
décider Secret par Secret.

Vous travaillez sur le cluster kubeadm, avec un namespace et une liaison
d'essai. Le challenge porte sur la configuration d'authentification de l'API
server, le kubelet du control plane et les liaisons anonymes du cluster : vous
le ferez seul, à la fin.

Page associée : [Restreindre l'accès à l'API server](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/restreindre-acces-api-server/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-restreindre-l-acces-anonyme
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl a les droits d'administrateur, et
`ssh` atteint les workers.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2.

## ⚖️ Exercice 1 : un anonyme et un authentifié, chemin par chemin

Une `SubjectAccessReview` demande à l'API server si une identité aurait le
droit d'agir, sans rien créer. Posez la même question pour quatre chemins,
d'abord au nom du groupe des anonymes (`system:unauthenticated`), puis au nom
du groupe de tout client authentifié (`system:authenticated`) :

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

Les deux groupes lisent `/version` et `/healthz` : c'est la liaison par
défaut `system:public-info-viewer`. Seul un client authentifié lit `/apis`, la
liste des API du cluster (liaison `system:discovery`). Aucun ne lit
`/metrics`. Une seule commande vous donne ainsi la carte de ce que chaque
groupe obtient avant même tout rôle personnel.

## 🚪 Exercice 2 : un droit donné à tout utilisateur authentifié

On pense à l'anonyme, on oublie l'autre groupe large : `system:authenticated`
contient **toute** identité que l'API server reconnaît, y compris un compte de
service d'un namespace quelconque. Donnez-lui le rôle `view`, puis demandez
si un inconnu authentifié lirait les Pods de `kube-system` :

```bash
kubectl create clusterrolebinding essai-ouvert --clusterrole=view --group=system:authenticated; printf 'un inconnu authentifié lit les pods de kube-system : '; kubectl auth can-i list pods -n kube-system --as=quiconque --as-group=system:authenticated
```

```text
clusterrolebinding.rbac.authorization.k8s.io/essai-ouvert created
un inconnu authentifié lit les pods de kube-system : yes
```

`yes` : n'importe quel compte du cluster lit maintenant tout le cluster.
Retrouvez les liaisons qui visent ce groupe :

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

Les liaisons `system:` et celle de Calico viennent de l'installation.
`essai-ouvert` est la vôtre : c'est ainsi qu'on repère une liaison ajoutée à
la main, en la comparant à la liste de départ. Retirez-la :

```bash
kubectl delete clusterrolebinding essai-ouvert
```

```text
clusterrolebinding.rbac.authorization.k8s.io "essai-ouvert" deleted
```

## 🔗 Exercice 3 : un kubelet ne lit que les Secrets de ses Pods

L'autorisation `Node` ne donne pas à un kubelet le droit de lire « les Secrets
de son nœud » en général : elle suit un graphe. Un kubelet lit un Secret
seulement si un Pod programmé sur **son** nœud s'en sert. Créez un namespace
d'essai et deux Secrets :

```bash
kubectl create namespace essai-graphe; kubectl -n essai-graphe create secret generic essai-monte --from-literal=cle=1; kubectl -n essai-graphe create secret generic essai-libre --from-literal=cle=2
```

```text
namespace/essai-graphe created
secret/essai-monte created
secret/essai-libre created
```

Lancez sur `k8s-w1.lab` un Pod qui monte seulement `essai-monte` :

```bash
kubectl -n essai-graphe run lecteur --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e --overrides='{"spec":{"nodeName":"k8s-w1.lab","volumes":[{"name":"s","secret":{"secretName":"essai-monte"}}],"containers":[{"name":"lecteur","image":"busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e","command":["sleep","3600"],"volumeMounts":[{"name":"s","mountPath":"/s"}]}]}}'; kubectl -n essai-graphe wait --for=condition=Ready pod/lecteur --timeout=90s
```

```text
pod/lecteur created
pod/lecteur condition met
```

Demandez maintenant, avec l'identité du kubelet de `k8s-w1.lab`, s'il lirait
chacun des deux Secrets :

```bash
for s in essai-monte essai-libre; do printf 'kubelet de k8s-w1, secret %-12s : ' $s; ssh -o StrictHostKeyChecking=no k8s-w1.lab sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf auth can-i get secret/$s -n essai-graphe; done
```

```text
kubelet de k8s-w1, secret essai-monte  : yes
kubelet de k8s-w1, secret essai-libre  : no - node: no relationship found between node 'k8s-w1.lab' and this object
```

Il lit `essai-monte`, que son Pod utilise. Il ne lit pas `essai-libre`,
pourtant dans le même namespace : `no relationship found`. Posez la même
question avec le kubelet du control plane :

```bash
printf 'kubelet de k8s-cp, secret essai-monte  : '; sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf auth can-i get secret/essai-monte -n essai-graphe
```

```text
kubelet de k8s-cp, secret essai-monte  : no - node: no relationship found between node 'k8s-cp.lab' and this object
```

Refusé aussi : aucun Pod de `k8s-cp.lab` ne monte ce Secret. Un nœud
compromis ne lit donc que les Secrets des Pods qu'il héberge déjà, pas ceux du
reste du cluster.

## 🧹 Nettoyage

Supprimez le namespace d'essai, ce qui retire le Pod et les deux Secrets, et
vérifiez que la liaison d'essai n'existe plus :

```bash
kubectl delete namespace essai-graphe --wait=true --timeout=120s; kubectl get clusterrolebinding essai-ouvert 2>&1 | tail -1
```

```text
namespace "essai-graphe" deleted
Error from server (NotFound): clusterrolebindings.rbac.authorization.k8s.io "essai-ouvert" not found
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-restreindre-l-acces-anonyme
dsoxlab check cks-restreindre-l-acces-anonyme
```

```text
╭─ Résultat : cks-restreindre-l-acces-anonyme ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un API server qui répond aux clients sans
identifiant, une liaison qui leur ouvre le cluster, et un kubelet qui accepte
tout le monde.

```bash
dsoxlab run cks-restreindre-l-acces-anonyme
dsoxlab challenge cks-restreindre-l-acces-anonyme
```
