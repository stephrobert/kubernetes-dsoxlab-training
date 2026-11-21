# Sauvegarder etcd, puis restaurer le cluster depuis un instantané

La leçon montre comment sauvegarder etcd avec `etcdctl snapshot save` et
restaurer le cluster avec `etcdutl snapshot restore`. Ce cours ajoute ce que
la leçon ne montre pas : vérifier le contenu d'une sauvegarde sans toucher au
cluster, en la restaurant dans un répertoire jetable lu par un etcd
temporaire, et reconnaître une sauvegarde abîmée.

Vous travaillez dans un répertoire d'essai, `/tmp/essai-sauvegarde`, avec un
namespace d'essai, `essai-sauvegarde`, et un etcd temporaire sur les ports
32379 et 32380. Le challenge porte sur une autre sauvegarde et sur le vrai
etcd du cluster : vous le ferez seul, à la fin.

Page associée : [Sauvegarde et restauration](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/backup-restore/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-etcd-backup-restore
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. `etcdctl` et
`etcdutl` sont installés sur le nœud. Ils demandent `sudo` pour lire les
certificats d'etcd.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et etcd 3.7.0.

## 💾 Exercice 1 : sauvegarder un état qu'on reconnaîtra

Créez un namespace et une ConfigMap témoin, puis sauvegardez etcd. Le client
utilise le certificat `healthcheck-client`, prévu par kubeadm pour parler à
etcd :

```bash
kubectl create namespace essai-sauvegarde; kubectl create configmap temoin -n essai-sauvegarde --from-literal=moment=avant-la-sauvegarde; sudo mkdir -p /tmp/essai-sauvegarde; sudo etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt --key=/etc/kubernetes/pki/etcd/healthcheck-client.key snapshot save /tmp/essai-sauvegarde/instantane.db 2>/dev/null; sudo ls -l /tmp/essai-sauvegarde
```

```text
namespace/essai-sauvegarde created
configmap/temoin created
Snapshot saved at /tmp/essai-sauvegarde/instantane.db
Server version 3.7.0
total 3312
-rw------- 1 root root 3387424 Nov 21 04:11 instantane.db
```

Supprimez le namespace, pour que le cluster et la sauvegarde ne disent plus
la même chose, puis vérifiez la sauvegarde :

```bash
kubectl delete namespace essai-sauvegarde; sudo etcdutl snapshot status /tmp/essai-sauvegarde/instantane.db -w table
```

```text
namespace "essai-sauvegarde" deleted
┌──────────┬──────────┬────────────┬────────────┬─────────┐
│   HASH   │ REVISION │ TOTAL KEYS │ TOTAL SIZE │ VERSION │
├──────────┼──────────┼────────────┼────────────┼─────────┤
│ 74e350a3 │     4545 │        682 │     3.4 MB │   3.7.0 │
└──────────┴──────────┴────────────┴────────────┴─────────┘
```

`snapshot status` lit le fichier sans le modifier : son empreinte, la révision
où il a été pris, le nombre de clés. C'est la vérification minimale. Elle dit
que le fichier est lisible, mais pas qu'il contient ce que vous attendez.

## 📂 Exercice 2 : restaurer dans un répertoire jetable

`etcdutl snapshot restore` fabrique un répertoire de données à partir de la
sauvegarde. Visez un répertoire d'essai, avec un nom de membre et des
adresses qui ne sont pas celles du vrai etcd :

```bash
sudo etcdutl snapshot restore /tmp/essai-sauvegarde/instantane.db --data-dir /tmp/essai-sauvegarde/donnees --name essai --initial-cluster essai=http://127.0.0.1:32380 --initial-advertise-peer-urls http://127.0.0.1:32380 2>&1 | tail -2; sudo ls /tmp/essai-sauvegarde/donnees/member
```

```text
2026-11-21T04:11:21Z	info	bbolt	bbolt@v1.5.0/db.go:327	Opening bbolt db (/tmp/essai-sauvegarde/donnees/member/snap/db) successfully
2026-11-21T04:11:21Z	info	snapshot/v3_snapshot.go:334	restored snapshot	{"path": "/tmp/essai-sauvegarde/instantane.db", "wal-dir": "/tmp/essai-sauvegarde/donnees/member/wal", "data-dir": "/tmp/essai-sauvegarde/donnees", "snap-dir": "/tmp/essai-sauvegarde/donnees/member/snap", "initial-memory-map-size": 10737418240}
snap
wal
```

Le répertoire contient les deux parties d'un etcd : `snap` (la base) et `wal`
(le journal). Le vrai etcd du cluster n'a pas été touché : il lit toujours
`/var/lib/etcd`.

## 🔎 Exercice 3 : interroger la sauvegarde avec un etcd temporaire

Lancez un second etcd, avec la même image que celui du cluster, sur ce
répertoire et sur les ports 32379 et 32380. Il tourne directement par
containerd (`ctr`), hors de Kubernetes :

```bash
IMG=$(kubectl -n kube-system get pod etcd-k8s-cp.lab -o jsonpath='{.spec.containers[0].image}'); sudo ctr -n k8s.io run -d --net-host --mount type=bind,src=/tmp/essai-sauvegarde/donnees,dst=/donnees,options=rbind:rw $IMG etcd-essai etcd --data-dir /donnees --name essai --listen-client-urls http://127.0.0.1:32379 --advertise-client-urls http://127.0.0.1:32379 --listen-peer-urls http://127.0.0.1:32380 --initial-cluster essai=http://127.0.0.1:32380 --initial-advertise-peer-urls "http://127.0.0.1:32380"; sleep 5; sudo etcdctl --endpoints=http://127.0.0.1:32379 endpoint health
```

```text
http://127.0.0.1:32379 is healthy: successfully committed proposal: took = 2.198295ms
```

Cherchez-y la ConfigMap témoin, puis le namespace dans le vrai cluster :

```bash
sudo etcdctl --endpoints=http://127.0.0.1:32379 get /registry/configmaps/essai-sauvegarde/temoin --print-value-only | tr -cd '[:print:]' | grep -o 'avant-la-sauvegarde'; kubectl get namespace essai-sauvegarde; echo "(le cluster, lui, ne l'a plus)"
```

```text
avant-la-sauvegarde
Error from server (NotFound): namespaces "essai-sauvegarde" not found
(le cluster, lui, ne l'a plus)
```

La sauvegarde contient bien le témoin, que le cluster n'a plus. Vous savez
maintenant que cette sauvegarde permettrait de le retrouver, sans avoir
risqué le cluster pour le vérifier. Arrêtez et supprimez l'etcd temporaire :

```bash
sudo ctr -n k8s.io task kill -s SIGKILL etcd-essai; sleep 2; sudo ctr -n k8s.io task delete etcd-essai; sudo ctr -n k8s.io container delete etcd-essai; sudo etcdctl --endpoints=http://127.0.0.1:32379 --command-timeout=2s endpoint health 2>&1 | tail -2; echo "(etcd temporaire arrêté)"
```

```text
time="2026-11-21T04:11:28Z" level=warning msg="task etcd-essai exit with non-zero exit code 137"
http://127.0.0.1:32379 is unhealthy: failed to commit proposal: context deadline exceeded
Error: unhealthy cluster
(etcd temporaire arrêté)
```

Le code 137 est celui d'un processus tué par `SIGKILL`, et l'etcd temporaire
ne répond plus.

## 🩹 Exercice 4 : une sauvegarde abîmée

Copiez la sauvegarde, coupez la copie en deux, et faites-la vérifier :

```bash
sudo cp /tmp/essai-sauvegarde/instantane.db /tmp/essai-sauvegarde/abimee.db; T=$(sudo stat -c %s /tmp/essai-sauvegarde/abimee.db); sudo truncate -s $((T / 2)) /tmp/essai-sauvegarde/abimee.db; sudo etcdutl snapshot status /tmp/essai-sauvegarde/abimee.db -w table > /tmp/essai-statut.txt 2>&1; echo "status : code $?"; head -2 /tmp/essai-statut.txt; rm -f /tmp/essai-statut.txt
```

```text
status : code 2
unexpected fault address 0x738af5b37000
fatal error: fault
```

`etcdutl` s'arrête en erreur (code 2) sur un message de bas niveau : il ne
sait pas lire la base. Un fichier copié à moitié, par un transfert
interrompu ou un disque plein, ressemble de l'extérieur à une sauvegarde. Il
faut toujours la vérifier là où elle est rangée, pas seulement au moment de
la prendre.

## 🧹 Nettoyage

Supprimez le répertoire d'essai :

```bash
sudo rm -rf /tmp/essai-sauvegarde
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-etcd-backup-restore
dsoxlab check cka-etcd-backup-restore
```

```text
╭─ Résultat : cka-etcd-backup-restore ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests     │
╰──────────────────────────────────────╯
```

0 sur 9 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : sauvegarder l'état courant, puis restaurer le vrai
cluster depuis la sauvegarde de la veille.

```bash
dsoxlab run cka-etcd-backup-restore
dsoxlab challenge cka-etcd-backup-restore
```
