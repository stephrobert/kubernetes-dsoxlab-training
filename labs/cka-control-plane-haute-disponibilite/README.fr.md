# Monter un plan de contrôle kubeadm à trois nœuds derrière un répartiteur, et en perdre un

La leçon montre comment monter un plan de contrôle à trois nœuds derrière un
répartiteur de charge, pour que le cluster survive à la perte d'une machine.
Le lab a préparé les machines sans cluster : le monter est le challenge. Ce
cours ne crée donc aucun cluster. Il ajoute des cas que la leçon ne montre
pas : un répartiteur qui accepte les connexions sans qu'aucune API ne
réponde, le point d'accès gravé dans le certificat de l'API server, la clé de
certificats, et le calcul du nombre de membres etcd qu'on peut perdre.

Vous travaillez dans un répertoire d'essai, `~/essai-ha`. Le challenge porte
sur le vrai cluster derrière `ha-lb.lab:6443` : vous le ferez seul, à la fin.

Page associée : [Plan de contrôle haute disponibilité](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ha-control-plane/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-control-plane-haute-disponibilite
```

Le lab monte quatre machines : trois futurs plans de contrôle et un
répartiteur HAProxy. Vous êtes maintenant connecté à `ha-cp1.lab`. Il n'y a
pas encore de cluster.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec kubeadm v1.37.

## ⚖️ Exercice 1 : un répartiteur qui répond sans API derrière

Regardez comment les noms des quatre machines se résolvent :

```bash
getent hosts ha-lb.lab ha-cp1.lab ha-cp2.lab ha-cp3.lab
```

```text
10.10.50.21     ha-lb.lab ha-lb
127.0.1.1       ha-cp1.lab.lab ha-cp1.lab ha-cp1 ha-cp1.lab
10.10.50.18     ha-cp1.lab.lab ha-cp1.lab ha-cp1 ha-cp1.lab
10.10.50.19     ha-cp2.lab ha-cp2
10.10.50.20     ha-cp3.lab ha-cp3
```

Le répartiteur `ha-lb.lab` a sa propre adresse, distincte des trois nœuds.
Testez-le de deux façons : une simple connexion TCP sur le port 6443, puis
une vraie requête HTTPS vers l'API :

```bash
nc -z -w 3 ha-lb.lab 6443; echo "connexion TCP au répartiteur : code $?"; curl -sk -m 5 "https://ha-lb.lab:6443/healthz"; echo "requête HTTPS : code $?"
```

```text
Connection to ha-lb.lab (10.10.50.21) 6443 port [tcp/*] succeeded!
connexion TCP au répartiteur : code 0
requête HTTPS : code 35
```

La connexion TCP réussit, mais la requête HTTPS échoue (code 35 de curl :
l'échange TLS n'a pas abouti). HAProxy accepte la connexion, puis ne trouve
aucun serveur d'API en marche derrière lui, et la coupe. Un port qui répond ne
prouve donc pas qu'une API répond : vérifiez toujours avec une requête qui va
jusqu'à l'API, comme `/healthz`.

## 🔏 Exercice 2 : le point d'accès est gravé dans le certificat

`kubeadm init` se découpe en phases, qu'on peut lancer une par une. Dans un
répertoire d'essai, faites générer une autorité de certification puis le
certificat de l'API server, avec le répartiteur comme point d'accès :

```bash
mkdir -p ~/essai-ha; kubeadm init phase certs ca --cert-dir ~/essai-ha/pki >/dev/null; kubeadm init phase certs apiserver --cert-dir ~/essai-ha/pki --control-plane-endpoint ha-lb.lab:6443 --apiserver-advertise-address $(hostname -I | cut -d' ' -f1); ls ~/essai-ha/pki
```

```text
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [ha-cp1.lab ha-lb.lab kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local] and IPs [10.96.0.1 10.10.50.18]
apiserver.crt
apiserver.key
ca.crt
ca.key
```

Lisez les noms que ce certificat couvre :

```bash
openssl x509 -in ~/essai-ha/pki/apiserver.crt -noout -ext subjectAltName
```

```text
X509v3 Subject Alternative Name: 
    DNS:ha-cp1.lab, DNS:ha-lb.lab, DNS:kubernetes, DNS:kubernetes.default, DNS:kubernetes.default.svc, DNS:kubernetes.default.svc.cluster.local, IP Address:10.96.0.1, IP Address:10.10.50.18
```

`ha-lb.lab` fait partie des noms du certificat, avec le nom du nœud et les
noms internes de Kubernetes. C'est pour cela que le point d'accès ne se change
plus après l'initialisation : les clients vérifient ce certificat, et un
nouveau nom n'y figurerait pas. Rien n'a été installé : tout est dans
`~/essai-ha`.

## 🔑 Exercice 3 : la clé de certificats

Avec `--upload-certs`, `kubeadm init` range les certificats du cluster dans un
Secret, chiffrés par une clé de certificats. Les autres plans de contrôle en
ont besoin pour rejoindre. Faites-en générer une :

```bash
kubeadm certs certificate-key; kubeadm certs certificate-key | wc -c
```

```text
6bed1af7ece6bf6f7b7fde11cad0400686e6ab46183d63688b68c495a38d19e0
65
```

64 caractères hexadécimaux (plus le retour à la ligne compté par `wc`), soit
une clé de 32 octets. Une nouvelle clé est tirée à chaque appel. Cette clé
donne accès aux certificats du cluster : elle se transmet comme un mot de
passe, et le Secret qu'elle protège est supprimé au bout de deux heures.

## 🗳️ Exercice 4 : combien de membres etcd peut-on perdre ?

etcd n'accepte une écriture que si une majorité de ses membres, le quorum,
est d'accord. Calculez, pour 1 à 5 membres, le quorum et le nombre de pannes
tolérées :

```bash
for n in 1 2 3 4 5; do q=$(( n / 2 + 1 )); echo "$n membres : quorum $q, panne tolérée $(( n - q ))"; done
```

```text
1 membres : quorum 1, panne tolérée 0
2 membres : quorum 2, panne tolérée 0
3 membres : quorum 2, panne tolérée 1
4 membres : quorum 3, panne tolérée 1
5 membres : quorum 3, panne tolérée 2
```

Trois membres tolèrent une panne, quatre membres aussi. Un nombre pair
n'apporte rien : il ajoute une machine qui peut tomber sans ajouter de
tolérance. C'est pour cela que le challenge, comme la plupart des clusters,
utilise trois plans de contrôle.

## 🧹 Nettoyage

Supprimez le répertoire d'essai :

```bash
rm -rf ~/essai-ha; ls ~/essai-ha 2>&1
```

```text
ls: cannot access '/home/ansible/essai-ha': No such file or directory
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-control-plane-haute-disponibilite
dsoxlab check cka-control-plane-haute-disponibilite
```

```text
╭─ Résultat : cka-control-plane-haute-disponibilite ─╮
│  0 / 100 pts                                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                   │
╰────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : monter le plan de contrôle à trois nœuds derrière
le répartiteur, puis prouver qu'il survit à la perte d'un nœud.

```bash
dsoxlab run cka-control-plane-haute-disponibilite
dsoxlab challenge cka-control-plane-haute-disponibilite
```
