# Repérer et retirer ce qu'un attaquant a laissé derrière lui

La leçon décrit les traces qu'un attaquant laisse dans un cluster pour y
revenir. Ce cours en plante trois lui-même, puis les chasse, avec des cas que
la leçon ne montre pas : un DaemonSet qui se fait passer pour un composant du
système, une liaison récente au rôle `cluster-admin` retrouvée par sa date, un
Pod qui monte tout le disque du nœud, et un jeton à l'ancienne qui n'expire
jamais.

Les traces d'essai portent des noms en `essai`. Le challenge porte sur
d'autres objets : vous le ferez seul, à la fin.

Page associée : [Persistance : ce qu'un attaquant laisse derrière lui](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/persistance-attaquant-cluster/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-detecter-une-persistance
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Plantez les trois traces d'essai : un compte de service lié à
`cluster-admin`, un DaemonSet nommé comme un composant du système qui monte la
racine de chaque nœud, et un jeton permanent pour le compte de service :

```bash
kubectl create namespace essai-chasse; kubectl create serviceaccount essai-maintenance -n essai-chasse; kubectl create clusterrolebinding essai-maintenance-admin --clusterrole=cluster-admin --serviceaccount=essai-chasse:essai-maintenance; cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kube-proxy-essai
  namespace: kube-system
spec:
  selector:
    matchLabels: {app: kube-proxy-essai}
  template:
    metadata:
      labels: {app: kube-proxy-essai}
    spec:
      containers:
        - name: proxy
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: [sleep, "3600"]
          volumeMounts: [{name: hote, mountPath: /hote}]
      volumes:
        - {name: hote, hostPath: {path: /}}
---
apiVersion: v1
kind: Secret
metadata:
  name: essai-jeton-permanent
  namespace: essai-chasse
  annotations: {kubernetes.io/service-account.name: essai-maintenance}
type: kubernetes.io/service-account-token
YAML
sleep 5
```

```text
namespace/essai-chasse created
serviceaccount/essai-maintenance created
clusterrolebinding.rbac.authorization.k8s.io/essai-maintenance-admin created
daemonset.apps/kube-proxy-essai created
secret/essai-jeton-permanent created
```

## 👑 Exercice 1 : les liaisons à cluster-admin, les plus récentes d'abord

Les liaisons d'origine datent de l'installation du cluster. Triez les
liaisons au rôle `cluster-admin` par date de création, et gardez les
dernières :

```bash
kubectl get clusterrolebindings --sort-by=.metadata.creationTimestamp -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.metadata.creationTimestamp}{"  "}{.metadata.name}{"\n"}{end}' | tail -3
```

```text
2026-11-21T10:43:44Z  kubeadm:cluster-admins
2026-11-21T10:43:45Z  cluster-admin
2026-11-21T11:04:21Z  essai-maintenance-admin
```

Les deux premières ont été créées par kubeadm à l'installation, à une seconde
d'écart. La troisième est arrivée vingt minutes plus tard : c'est elle qu'il
faut expliquer.

## 🎭 Exercice 2 : un composant du système qui n'en est pas un

Un nom qui commence par `kube-` dans `kube-system` ne prouve rien. Comparez
les DaemonSets de `kube-system` par date et par image :

```bash
kubectl get daemonsets -n kube-system -o custom-columns='NOM:.metadata.name,CREE:.metadata.creationTimestamp,IMAGE:.spec.template.spec.containers[0].image'
```

```text
NOM                CREE                   IMAGE
kube-proxy         2026-11-21T10:43:46Z   registry.k8s.io/kube-proxy:v1.37.2
kube-proxy-essai   2026-11-21T11:04:21Z   busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

Le vrai `kube-proxy` vient de `registry.k8s.io` et date de l'installation.
`kube-proxy-essai` lance une image busybox et date d'aujourd'hui : un faux.

## 💽 Exercice 3 : les Pods qui montent le disque d'un nœud

Un Pod qui monte `/` du nœud peut lire et modifier tout son système. Cherchez
les Pods dont un volume `hostPath` pointe sur la racine :

```bash
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{" "}{.spec.volumes[*].hostPath.path}{"\n"}{end}' | grep -E ' /( |$)'
```

```text
kube-system/kube-proxy-essai-4jhqv /
kube-system/kube-proxy-essai-5d46m /
kube-system/kube-proxy-essai-7m4z2 /
kube-system/kube-proxy-essai-qdjzg /
```

Un Pod par nœud, ceux du faux DaemonSet. Les composants du control plane
montent aussi des répertoires du nœud, mais jamais la racine entière.

## 🔑 Exercice 4 : les jetons qui n'expirent jamais

Un Secret de type `service-account-token` porte un jeton qui reste valable
tant que le Secret existe, sans date d'expiration. Les jetons normaux, eux,
expirent. Listez ces Secrets dans tout le cluster :

```bash
kubectl get secrets -A --field-selector type=kubernetes.io/service-account-token -o custom-columns='NS:.metadata.namespace,NOM:.metadata.name,COMPTE:.metadata.annotations.kubernetes\.io/service-account\.name'
```

```text
NS             NOM                     COMPTE
essai-chasse   essai-jeton-permanent   essai-maintenance
```

Un seul, pour le compte `essai-maintenance`, celui qui est lié à
`cluster-admin` : un accès administrateur permanent.

## 🗂️ Exercice 5 : consigner, puis retirer

Avant de supprimer une trace, gardez-en une copie : elle servira à comprendre
l'attaque. Exportez le DaemonSet et la liaison :

```bash
kubectl get daemonset kube-proxy-essai -n kube-system -o yaml > ~/constat-essai.yaml; kubectl get clusterrolebinding essai-maintenance-admin -o yaml >> ~/constat-essai.yaml; grep -c '^kind:' ~/constat-essai.yaml
```

```text
2
```

Deux objets consignés. Retirez maintenant les trois traces :

```bash
kubectl delete daemonset kube-proxy-essai -n kube-system; kubectl delete clusterrolebinding essai-maintenance-admin; kubectl delete namespace essai-chasse; sleep 10; kubectl get pods -n kube-system -l app=kube-proxy-essai
```

```text
daemonset.apps "kube-proxy-essai" deleted from kube-system namespace
clusterrolebinding.rbac.authorization.k8s.io "essai-maintenance-admin" deleted
namespace "essai-chasse" deleted
NAME                     READY   STATUS        RESTARTS   AGE
kube-proxy-essai-4jhqv   1/1     Terminating   0          21s
kube-proxy-essai-7m4z2   1/1     Terminating   0          21s
```

Les Pods du faux DaemonSet sont en cours d'arrêt : supprimer le DaemonSet
supprime aussi ce qu'il a lancé. La suppression du namespace emporte le
compte de service et son jeton.

## 🧹 Nettoyage

Supprimez le fichier de constat :

```bash
rm -f ~/constat-essai.yaml
```

```text

```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-detecter-une-persistance
dsoxlab check k8s-detecter-une-persistance
```

```text
╭─ Résultat : k8s-detecter-une-persistance ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests          │
╰───────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un attaquant est passé dans le cluster. Retrouvez ce
qui lui redonne l'accès, consignez-le, puis retirez-le sans abîmer
l'application légitime.

```bash
dsoxlab run k8s-detecter-une-persistance
dsoxlab challenge k8s-detecter-une-persistance
```
