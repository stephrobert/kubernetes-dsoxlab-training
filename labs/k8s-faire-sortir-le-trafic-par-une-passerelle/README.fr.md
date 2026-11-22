# Faire sortir le trafic par une passerelle

La leçon active la passerelle d'egress de Cilium pour qu'un Pod sorte du
cluster toujours par le même nœud, donc avec la même adresse. C'est aussi le
challenge du lab : ce cours n'active rien et n'écrit aucune politique. Il
regarde comment le trafic sort **aujourd'hui**, sans passerelle : quelle
adresse un serveur extérieur voit selon le nœud du Pod, quelle règle réécrit
cette adresse, et quand elle ne la réécrit pas. C'est ce qu'il faut savoir
pour comprendre ce que la passerelle change.

Vous travaillez dans le namespace `essai-sortie`, avec deux clients et deux
serveurs d'essai. Le challenge porte sur d'autres Pods, dans `egress-demo` :
vous le ferez seul, à la fin.

Page associée : [Faire sortir le trafic par une passerelle d'egress](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/egress-gateway/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-faire-sortir-le-trafic-par-une-passerelle
```

Vous êtes maintenant connecté à `net-cp.lab`, le plan de contrôle du cluster
Cilium. Le serveur témoin du lab tourne sur `k8s-cp.lab`, hors du cluster, et
répond par l'adresse source qu'il voit. Posez les objets d'essai : un client
sur chaque worker, un serveur web sur `net-w2`, et un second serveur web sur
`net-w2` qui partage le réseau du nœud (`hostNetwork: true`) :

```bash
kubectl create namespace essai-sortie; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: client-w1
  namespace: essai-sortie
spec:
  nodeName: net-w1.lab
  containers:
    - name: c
      image: busybox:1.38.0
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: client-w2
  namespace: essai-sortie
spec:
  nodeName: net-w2.lab
  containers:
    - name: c
      image: busybox:1.38.0
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: web-w2
  namespace: essai-sortie
spec:
  nodeName: net-w2.lab
  containers:
    - name: web
      image: nginx:1.30.6
---
apiVersion: v1
kind: Pod
metadata:
  name: web-hote-w2
  namespace: essai-sortie
spec:
  nodeName: net-w2.lab
  hostNetwork: true
  containers:
    - name: web
      image: nginx:1.30.6
YAML
kubectl -n essai-sortie wait --for=condition=Ready pod --all --timeout=120s
kubectl -n essai-sortie get pods -o wide
```

```text
NAME          READY   STATUS    RESTARTS   AGE   IP             NODE         NOMINATED NODE   READINESS GATES
client-w1     1/1     Running   0          1s    10.244.1.245   net-w1.lab   <none>           <none>
client-w2     1/1     Running   0          1s    10.244.2.10    net-w2.lab   <none>           <none>
web-hote-w2   1/1     Running   0          1s    10.10.50.16    net-w2.lab   <none>           <none>
web-w2        1/1     Running   0          1s    10.244.2.197   net-w2.lab   <none>           <none>
```

`web-hote-w2` porte l'adresse du nœud `net-w2`, `10.10.50.16` : il écoute
directement sur le nœud. Les sorties montrées dans ce cours ont été relevées
sur ces machines le 22 novembre 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🌐 Exercice 1 : l'adresse de sortie dépend du nœud

Lisez l'adresse du témoin dans la ConfigMap du lab, puis appelez-le depuis
chaque client :

```bash
temoin=$(kubectl -n egress-demo get cm -o jsonpath='{.items[*].data.url}')
echo "$temoin"
for p in client-w1 client-w2; do echo "$p -> $(kubectl -n essai-sortie exec $p -- wget -qO- $temoin)"; done
```

```text
http://10.10.50.11:8090/
client-w1 -> 10.10.50.15
client-w2 -> 10.10.50.16
```

Le témoin ne voit jamais l'adresse d'un Pod (`10.244.x.x`) : il voit
l'adresse du **nœud** qui porte le Pod, `10.10.50.15` pour `net-w1` et
`10.10.50.16` pour `net-w2`. Le même Pod, replacé sur un autre nœud,
sortirait avec une autre adresse. Un pare-feu extérieur qui n'autorise
qu'une adresse ne peut donc pas viser un Pod. C'est ce problème que la
passerelle d'egress règle.

## 🔁 Exercice 2 : la règle qui réécrit l'adresse

Ce cluster masque les adresses avec iptables : la ligne
`Masquerading: IPTables` que montre la leçon. Cilium pose sa règle dans la
chaîne `CILIUM_POST_nat` de chaque nœud. Lisez celle de `net-w1`, et son
compteur avant et après un appel au témoin :

```bash
ssh net-w1.lab 'sudo iptables -t nat -S CILIUM_POST_nat | grep non-cluster'
ssh net-w1.lab 'sudo iptables -t nat -L CILIUM_POST_nat -n -v -x | grep non-cluster' | awk '{print "avant :", $1, "paquets"}'
kubectl -n essai-sortie exec client-w1 -- wget -qO- $temoin
ssh net-w1.lab 'sudo iptables -t nat -L CILIUM_POST_nat -n -v -x | grep non-cluster' | awk '{print "après :", $1, "paquets"}'
```

```text
-A CILIUM_POST_nat -s 10.244.1.0/24 ! -d 10.244.1.0/24 ! -o cilium_+ -m comment --comment "cilium masquerade non-cluster" -j MASQUERADE
avant : 6 paquets
10.10.50.15
après : 7 paquets
```

La règle se lit en trois conditions. Le paquet vient d'un Pod de ce nœud
(`-s 10.244.1.0/24`, le bloc d'adresses de `net-w1`), il ne va pas vers un
Pod de ce nœud (`! -d 10.244.1.0/24`), et il ne sort pas par une interface de
Cilium (`! -o cilium_+`). Alors `MASQUERADE` remplace sa source par l'adresse
de l'interface de sortie. Le compteur n'avance que d'**un** paquet pour toute
la requête HTTP : seul le premier paquet d'une connexion traverse la table
`nat`, le noyau applique ensuite la même traduction au reste de la connexion.

## 🔀 Exercice 3 : d'un Pod à l'autre, l'adresse est gardée

Appelez maintenant le serveur `web-w2`, sur l'autre nœud, par l'adresse de son
Pod, et lisez dans son journal l'adresse qu'il a vue :

```bash
web=$(kubectl -n essai-sortie get pod web-w2 -o jsonpath='{.status.podIP}')
cip=$(kubectl -n essai-sortie get pod client-w1 -o jsonpath='{.status.podIP}')
echo "client-w1=$cip web-w2=$web"
kubectl -n essai-sortie exec client-w1 -- wget -qO /dev/null "http://$web/?essai-pod"
kubectl -n essai-sortie logs web-w2 | grep essai-pod | cut -d' ' -f1-7
```

```text
client-w1=10.244.1.245 web-w2=10.244.2.197
10.244.1.245 - - [22/Nov/2026:22:39:52 +0000] "GET /?essai-pod
```

Le serveur voit `10.244.1.245`, l'adresse du Pod client : rien n'a été
masqué. Le paquet allait pourtant hors du bloc de `net-w1`, mais il est
sorti par le tunnel de Cilium, une interface `cilium_*`, et la troisième
condition de la règle l'a laissé passer. Entre deux Pods, Kubernetes exige
que chacun voie la vraie adresse de l'autre, et c'est ce qui permet à une
NetworkPolicy de reconnaître la source.

## 🖥️ Exercice 4 : vers un nœud, l'adresse est masquée

Appelez enfin `web-hote-w2`, qui écoute sur le nœud `net-w2` lui-même, par
l'adresse du nœud :

```bash
kubectl -n essai-sortie exec client-w1 -- wget -qO /dev/null "http://10.10.50.16/?essai-noeud"
kubectl -n essai-sortie logs web-hote-w2 | grep essai-noeud | cut -d' ' -f1-7
```

```text
10.10.50.15 - - [22/Nov/2026:22:39:52 +0000] "GET /?essai-noeud
```

Même client, même nœud de destination, mais cette fois le serveur voit
`10.10.50.15`, l'adresse de `net-w1`. La destination, `10.10.50.16`, n'est
pas une adresse de Pod : le paquet est sorti par `enp1s0`, l'interface du
réseau des nœuds, et la règle de l'exercice 2 l'a masqué. Ce qui décide n'est
pas la machine visée, mais **l'interface par laquelle le paquet sort**.

## 🧹 Nettoyage

Supprimez le namespace d'essai, et vérifiez que les deux Pods du challenge
sont toujours là :

```bash
kubectl delete namespace essai-sortie --wait=true --timeout=120s
kubectl -n egress-demo get pods
```

```text
namespace "essai-sortie" deleted
NAME               READY   STATUS    RESTARTS   AGE
autre              1/1     Running   0          2m12s
sortie-controlee   1/1     Running   0          2m12s
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-faire-sortir-le-trafic-par-une-passerelle
dsoxlab check k8s-faire-sortir-le-trafic-par-une-passerelle
```

```text
╭─ Résultat : k8s-faire-sortir-le-trafic-par-une-passerelle ─╮
│  0 / 100 pts                                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                           │
╰────────────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : activer la passerelle d'egress et faire sortir un
seul Pod par un nœud choisi, pendant que son voisin continue de sortir par
le sien.

```bash
dsoxlab run k8s-faire-sortir-le-trafic-par-une-passerelle
dsoxlab challenge k8s-faire-sortir-le-trafic-par-une-passerelle
```
