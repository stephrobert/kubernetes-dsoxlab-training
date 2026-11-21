# Contrôler la santé d'etcd et défragmenter sa base

La leçon montre etcd, la base où Kubernetes range tous ses objets, et les
commandes d'`etcdctl` qui contrôlent sa santé. Ce cours vous fait regarder
dans la base elle-même, et ajoute des cas que la leçon ne montre pas : une clé
écrite sans passer par l'API, un objet Kubernetes tel qu'etcd le range, la
révision qui avance à chaque écriture, le compactage qui efface l'historique,
et l'état du membre lu par un script.

Vous travaillez avec des clés d'essai sous le préfixe `/essai-cours/` et un
namespace d'essai, `essai-etcd`. Le challenge porte sur d'autres questions :
vous le ferez seul, à la fin.

Page associée : [etcd](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/etcd/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-etcd-sante-et-defragmentation
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

`etcdctl` est appelé dans le Pod etcd du nœud, avec les certificats du
serveur etcd, comme dans la leçon. La commande est longue, mais elle est
toujours la même : seule la fin change.

## ✍️ Exercice 1 : écrire et lire une clé hors de l'API

Écrivez une clé directement dans etcd, puis relisez-la :

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key put /essai-cours/note 'ecrite par etcdctl'; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note
```

```text
OK
/essai-cours/note
ecrite par etcdctl
```

Listez les clés du préfixe, puis demandez à l'API les ConfigMaps de
`default` :

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/ --prefix --keys-only; kubectl get --raw /api/v1/namespaces/default/configmaps | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["items"]), "ConfigMap dans default : la clé ne se voit pas par l API")'
```

```text
/essai-cours/note

1 ConfigMap dans default : la clé ne se voit pas par l API
```

La clé existe dans etcd, mais l'API ne la montre nulle part : elle ne lit que
les clés qu'elle a elle-même rangées, sous `/registry/`. Écrire dans etcd à la
main contourne toutes les vérifications de l'API. On ne le fait que pour
apprendre, ou pour réparer.

## 🗂️ Exercice 2 : un objet Kubernetes dans etcd

Créez une ConfigMap, puis cherchez-la dans etcd :

```bash
kubectl create namespace essai-etcd; kubectl create configmap fiche -n essai-etcd --from-literal=couleur=bleu; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /registry/configmaps/essai-etcd/fiche --keys-only
```

```text
namespace/essai-etcd created
configmap/fiche created
/registry/configmaps/essai-etcd/fiche
```

L'objet est rangé sous `/registry/<type>/<namespace>/<nom>`. Lisez le début de
sa valeur, caractère par caractère :

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /registry/configmaps/essai-etcd/fiche --print-value-only | head -c 120 | od -c | head -3
```

```text
0000000   k   8   s  \0  \n 017  \n 002   v   1 022  \t   C   o   n   f
0000020   i   g   M   a   p 022 272 001  \n 246 001  \n 005   f   i   c
0000040   h   e 022  \0 032  \n   e   s   s   a   i   -   e   t   c   d
```

Ce n'est ni du JSON ni du YAML : le préfixe `k8s` suivi de données binaires
(Protobuf). On reconnaît `v1`, `ConfigMap`, `fiche` et `essai-etcd`. Lire etcd
directement ne remplace donc pas `kubectl get` : c'est l'API qui sait décoder.

## 🔢 Exercice 3 : chaque écriture fait avancer la révision

etcd numérote chaque modification de la base : c'est la révision. Lisez la
révision du cluster et la version de la clé :

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("révision du cluster", d["header"]["revision"], "| version de la clé", d["kvs"][0]["version"])'
```

```text
révision du cluster 2974 | version de la clé 1
```

Écrivez trois fois la clé, et relisez :

```bash
for i in 1 2 3; do kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key put /essai-cours/note "version $i" >/dev/null; done; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("révision du cluster", d["header"]["revision"], "| version de la clé", d["kvs"][0]["version"], "| créée à", d["kvs"][0]["create_revision"], "| modifiée à", d["kvs"][0]["mod_revision"])'
```

```text
révision du cluster 2977 | version de la clé 4 | créée à 2967 | modifiée à 2977
```

La clé en est à sa version 4, et la révision a avancé de 3. La révision vaut
pour toute la base : toute écriture, de n'importe quel objet, la fait
avancer.

## 🗜️ Exercice 4 : relire le passé, puis le compacter

etcd garde les anciennes versions. Relisez la clé telle qu'elle était à sa
création :

```bash
CREE=$(kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["kvs"][0]["create_revision"])'); echo "lecture à la révision $CREE :"; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note --rev=$CREE --print-value-only
```

```text
lecture à la révision 2967 :
ecrite par etcdctl
```

La première valeur est revenue. Compactez maintenant l'historique jusqu'à la
révision courante :

```bash
REV=$(kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["header"]["revision"])'); kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key compact $REV
```

```text
compacted revision 2977
```

Relisez l'ancienne version :

```bash
CREE=$(kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["kvs"][0]["create_revision"])'); kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note --rev=$CREE; echo "(code de la relecture)"
```

```text
{"level":"warn","ts":"2026-11-21T04:03:06.587575Z","logger":"etcd-client","caller":"v3/retry_interceptor.go:68","msg":"retrying of unary invoker failed","target":"etcd-endpoints://0xfeb4efeee00/127.0.0.1:2379","peer":"Peer{Addr: '127.0.0.1:2379', LocalAddr: '127.0.0.1:34442', AuthInfo: 'tls'}","method":"/etcdserverpb.KV/Range","attempt":0,"error":"rpc error: code = OutOfRange desc = etcdserver: mvcc: required revision has been compacted"}
Error: etcdserver: mvcc: required revision has been compacted
command terminated with exit code 1
(code de la relecture)
```

`required revision has been compacted` : l'historique antérieur est effacé.
L'API server demande ce compactage tout seul, toutes les 5 minutes par défaut.
Le compactage retire les anciennes versions, mais ne rend pas la place sur le
disque : c'est le rôle de la défragmentation, que demande le challenge.

## 📊 Exercice 5 : l'état du membre lu par un script

`etcdctl endpoint status` peut répondre en JSON, plus facile à lire par un
script que le tableau. Extrayez la taille de la base, la place réellement
utilisée, et le leader :

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key endpoint status -w json | python3 -c 'import json,sys; s=json.load(sys.stdin)[0]["Status"]; print("taille", s["dbSize"], "en usage", s["dbSizeInUse"], "leader", hex(s["leader"]))'
```

```text
taille 150855680 en usage 2957312 leader 0x2e830b06b400c72b
```

La base occupe environ 150 Mo, mais seuls 3 Mo servent encore. L'écart est la
place que le compactage a libérée sans la rendre au disque.

## 🧹 Nettoyage

Supprimez les clés d'essai et le namespace. `etcdctl del` affiche le nombre
de clés supprimées :

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key del /essai-cours/ --prefix; kubectl delete namespace essai-etcd
```

```text
1
namespace "essai-etcd" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-etcd-sante-et-defragmentation
dsoxlab check cka-etcd-sante-et-defragmentation
```

```text
╭─ Résultat : cka-etcd-sante-et-defragmentation ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests               │
╰────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : relever l'identité et la santé du membre etcd, son
quota, et rendre au disque la place perdue.

```bash
dsoxlab run cka-etcd-sante-et-defragmentation
dsoxlab challenge cka-etcd-sante-et-defragmentation
```
