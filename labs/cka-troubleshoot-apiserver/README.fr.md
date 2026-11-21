# Remettre l'API server en service

La leçon montre comment dépanner un plan de contrôle quand l'API server ne
répond plus. Dans ce lab, il est en panne : c'est le challenge, et kubectl ne
sert à rien. Ce cours ne touche pas à l'API server. Il vous fait vérifier les
autres composants par leurs propres moyens, et ajoute des cas que la leçon ne
montre pas : le point de santé local de chaque composant, un composant
statique arrêté puis relancé en déplaçant son manifeste, et etcd interrogé
sans l'API.

Le challenge porte sur l'API server lui-même : vous le ferez seul, à la fin.

Page associée : [Dépanner un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-apiserver
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Les outils du nœud (`crictl`, les fichiers de
`/etc/kubernetes`) demandent `sudo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🩺 Exercice 1 : chaque composant a son propre point de santé

Le scheduler, le controller-manager et le kubelet ont chacun un point de
santé, sur un port local du nœud. Interrogez-les directement :

```bash
for p in 10259 10257; do printf 'port %s : ' $p; curl -sk "https://127.0.0.1:$p/healthz"; echo; done; printf 'kubelet 10248 : '; curl -s "http://127.0.0.1:10248/healthz"; echo
```

```text
port 10259 : ok
port 10257 : ok
kubelet 10248 : ok
```

Les trois répondent `ok`, sans passer par l'API server (le scheduler sur
10259, le controller-manager sur 10257, le kubelet sur 10248). Comparez avec
kubectl :

```bash
kubectl get nodes --request-timeout=5s 2>&1 | tail -1
```

```text
The connection to the server 10.10.50.11:6443 was refused - did you specify the right host or port?
```

Connexion refusée sur le port 6443 : c'est l'API server qui manque, pas tout
le plan de contrôle. Interroger chaque composant sépare ce qui marche de ce
qui ne marche pas.

## 🔁 Exercice 2 : arrêter et relancer un composant statique sans l'API

Les composants du plan de contrôle sont des Pods statiques : le kubelet les
lance à partir des fichiers de `/etc/kubernetes/manifests`. Comptez les
conteneurs du scheduler :

```bash
sudo crictl ps --name kube-scheduler -o json | python3 -c 'import json,sys; c=json.load(sys.stdin)["containers"]; print(len(c), "conteneur(s) kube-scheduler")'
```

```text
1 conteneur(s) kube-scheduler
```

Sortez son manifeste du répertoire, attendez, puis recomptez et interrogez
son port :

```bash
sudo mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/kube-scheduler.yaml; sleep 25; sudo crictl ps --name kube-scheduler -q | wc -l; printf 'port 10259 : '; curl -sk -m 3 "https://127.0.0.1:10259/healthz"; echo " (code $?)"
```

```text
0
port 10259 :  (code 7)
```

Plus aucun conteneur, et le port ne répond plus (code 7 de curl : connexion
impossible). Le kubelet a arrêté le Pod dès que son fichier a disparu.
Remettez le manifeste en place :

```bash
sudo mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/kube-scheduler.yaml; sleep 30; sudo crictl ps --name kube-scheduler | tail -1 | cut -c1-110; printf 'port 10259 : '; curl -sk "https://127.0.0.1:10259/healthz"; echo
```

```text
7a2cf2aca8597       20824b0c11f7d       29 seconds ago      Running             kube-scheduler      1         
port 10259 : ok
```

Le scheduler repart, avec un nouveau conteneur. Déplacer un manifeste hors du
répertoire, et non le modifier sur place, est la façon sûre d'arrêter un
composant statique : le fichier est conservé, et le remettre suffit.

## 🗄️ Exercice 3 : etcd répond, même quand l'API se tait

etcd est un Pod statique lui aussi. Entrez dans son conteneur avec `crictl
exec`, sans l'API, et demandez sa santé :

```bash
C=$(sudo crictl ps --name etcd -q | head -1); sudo crictl exec $C etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key endpoint health
```

```text
127.0.0.1:2379 is healthy: successfully committed proposal: took = 5.624025ms
```

Sain. Lisez les premiers namespaces rangés dans la base :

```bash
C=$(sudo crictl ps --name etcd -q | head -1); sudo crictl exec $C etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /registry/namespaces --prefix --keys-only | head -5
```

```text
/registry/namespaces/calico-system

/registry/namespaces/default

/registry/namespaces/kube-node-lease
```

Les données du cluster sont intactes : c'est seulement le serveur qui les
expose qui est tombé. Savoir qu'etcd va bien évite de chercher la panne au
mauvais endroit.

## 🧹 Nettoyage

Vérifiez que le manifeste du scheduler est bien revenu à sa place :

```bash
sudo test -f /etc/kubernetes/manifests/kube-scheduler.yaml && echo 'manifeste du scheduler en place'
```

```text
manifeste du scheduler en place
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-apiserver
dsoxlab check cka-troubleshoot-apiserver
```

```text
╭─ Résultat : cka-troubleshoot-apiserver ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests        │
╰─────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un API server qui ne démarre plus, à remettre en
service sans l'ouvrir à tout le monde.

```bash
dsoxlab run cka-troubleshoot-apiserver
dsoxlab challenge cka-troubleshoot-apiserver
```
