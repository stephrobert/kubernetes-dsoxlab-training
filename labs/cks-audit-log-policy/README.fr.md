# Tracer qui lit les Secrets avec l'audit de l'API server

La leçon montre comment écrire une politique d'audit et l'activer sur l'API
server. Ce cours fait lire un vrai journal d'audit, pour trois points qu'elle
ne montre pas : une requête qui produit deux événements, l'ordre des règles de
la politique, et une action faite sous une autre identité.

Pour ne pas toucher à l'API server du lab, dont la configuration est le sujet
du challenge, vous lancez un **API server d'essai** : le même programme, sur
le port 6444, avec sa propre politique et son propre journal dans
`/tmp/essai-audit`. Il partage l'etcd du cluster, sous un préfixe à part,
`/essai-audit`, et ne voit donc aucun objet du cluster. Il autorise tout
(`AlwaysAllow`) et n'écoute que sur `127.0.0.1` : c'est un outil d'exercice,
jamais un réglage à recopier.

Page associée : [Audit Logs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-audit-log-policy
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane).

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2.

Préparez l'API server d'essai : copiez le programme de l'API server du
cluster, écrivez une politique qui enregistre tout au niveau des métadonnées,
et lancez-le. La commande attend qu'il réponde :

```bash
sudo mkdir -p /tmp/essai-audit; P=$(pgrep -xo kube-apiserver); sudo cp /proc/$P/root/usr/local/bin/kube-apiserver /tmp/essai-audit/; cat <<'YAML' | sudo tee /tmp/essai-audit/politique.yaml > /dev/null
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
YAML
sudo bash -c 'nohup /tmp/essai-audit/kube-apiserver --secure-port=6444 --bind-address=127.0.0.1 --cert-dir=/tmp/essai-audit/certs --etcd-servers=https://127.0.0.1:2379 --etcd-prefix=/essai-audit --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key --client-ca-file=/etc/kubernetes/pki/ca.crt --authorization-mode=AlwaysAllow --service-cluster-ip-range=10.96.0.0/12 --service-account-issuer=https://essai-audit --service-account-key-file=/etc/kubernetes/pki/sa.pub --service-account-signing-key-file=/etc/kubernetes/pki/sa.key --audit-policy-file=/tmp/essai-audit/politique.yaml --audit-log-path=/tmp/essai-audit/audit.log > /tmp/essai-audit/serveur.log 2>&1 & echo $! > /tmp/essai-audit/pid'; until sudo test -f /tmp/essai-audit/certs/apiserver.crt && sudo chmod 0644 /tmp/essai-audit/certs/apiserver.crt && kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get --raw /livez > /dev/null 2>&1; do sleep 2; done; echo 'API server de test prêt'
```

```text
API server de test prêt
```

Toutes les commandes `kubectl` de ce cours visent ce serveur avec
`--server=https://127.0.0.1:6444`. Il retient son PID dans
`/tmp/essai-audit/pid`, ce qui sert à l'arrêter. Une politique d'audit n'est
lue qu'au démarrage : chaque changement de politique impose de le relancer.

## 📨 Exercice 1 : une requête, deux événements

Listez les namespaces du serveur d'essai, puis lisez ce que le journal a
retenu de cette requête :

```bash
kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get namespaces > /dev/null; sudo jq -c 'select(.verb=="list" and .objectRef.resource=="namespaces") | {stage, level, utilisateur: .user.username, verb, ressource: .objectRef.resource}' /tmp/essai-audit/audit.log | tail -2
```

```text
{"stage":"RequestReceived","level":"Metadata","utilisateur":"kubernetes-admin","verb":"list","ressource":"namespaces"}
{"stage":"ResponseComplete","level":"Metadata","utilisateur":"kubernetes-admin","verb":"list","ressource":"namespaces"}
```

Une seule requête, deux événements. Le premier est écrit à la réception
(`RequestReceived`), le second quand la réponse est partie
(`ResponseComplete`). Sur un vrai cluster, ce doublon pèse sur le volume du
journal : c'est ce que retire `omitStages`.

## 🔀 Exercice 2 : la première règle qui correspond gagne

Écrivez une politique qui veut enregistrer les ConfigMaps en entier
(`RequestResponse`), mais qui place d'abord une règle générale au niveau
Metadata. Relancez le serveur, créez une ConfigMap, et lisez son niveau :

```bash
cat <<'YAML' | sudo tee /tmp/essai-audit/politique.yaml > /dev/null
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
  - level: RequestResponse
    resources:
      - group: ""
        resources: [configmaps]
YAML
sudo kill $(sudo cat /tmp/essai-audit/pid); sleep 3; sudo bash -c 'nohup /tmp/essai-audit/kube-apiserver --secure-port=6444 --bind-address=127.0.0.1 --cert-dir=/tmp/essai-audit/certs --etcd-servers=https://127.0.0.1:2379 --etcd-prefix=/essai-audit --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key --client-ca-file=/etc/kubernetes/pki/ca.crt --authorization-mode=AlwaysAllow --service-cluster-ip-range=10.96.0.0/12 --service-account-issuer=https://essai-audit --service-account-key-file=/etc/kubernetes/pki/sa.pub --service-account-signing-key-file=/etc/kubernetes/pki/sa.key --audit-policy-file=/tmp/essai-audit/politique.yaml --audit-log-path=/tmp/essai-audit/audit.log > /tmp/essai-audit/serveur.log 2>&1 & echo $! > /tmp/essai-audit/pid'; until sudo test -f /tmp/essai-audit/certs/apiserver.crt && sudo chmod 0644 /tmp/essai-audit/certs/apiserver.crt && kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get --raw /livez > /dev/null 2>&1; do sleep 2; done; echo 'API server de test prêt'; kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt create configmap essai-ordre --from-literal=cle=valeur > /dev/null; sudo jq -c 'select(.verb=="create" and .objectRef.name=="essai-ordre") | {stage, level}' /tmp/essai-audit/audit.log
```

```text
API server de test prêt
{"stage":"ResponseComplete","level":"Metadata"}
```

`Metadata` : la première règle correspond à toutes les requêtes, donc la
seconde n'est jamais lue. L'API server parcourt les règles dans l'ordre, et
s'arrête à la première qui correspond. Inversez l'ordre, et retirez l'étape
`RequestReceived` :

```bash
cat <<'YAML' | sudo tee /tmp/essai-audit/politique.yaml > /dev/null
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: [RequestReceived]
rules:
  - level: RequestResponse
    resources:
      - group: ""
        resources: [configmaps]
  - level: Metadata
YAML
sudo kill $(sudo cat /tmp/essai-audit/pid); sleep 3; sudo bash -c 'nohup /tmp/essai-audit/kube-apiserver --secure-port=6444 --bind-address=127.0.0.1 --cert-dir=/tmp/essai-audit/certs --etcd-servers=https://127.0.0.1:2379 --etcd-prefix=/essai-audit --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key --client-ca-file=/etc/kubernetes/pki/ca.crt --authorization-mode=AlwaysAllow --service-cluster-ip-range=10.96.0.0/12 --service-account-issuer=https://essai-audit --service-account-key-file=/etc/kubernetes/pki/sa.pub --service-account-signing-key-file=/etc/kubernetes/pki/sa.key --audit-policy-file=/tmp/essai-audit/politique.yaml --audit-log-path=/tmp/essai-audit/audit.log > /tmp/essai-audit/serveur.log 2>&1 & echo $! > /tmp/essai-audit/pid'; until sudo test -f /tmp/essai-audit/certs/apiserver.crt && sudo chmod 0644 /tmp/essai-audit/certs/apiserver.crt && kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get --raw /livez > /dev/null 2>&1; do sleep 2; done; echo 'API server de test prêt'; kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt create configmap essai-ordre-2 --from-literal=cle=valeur > /dev/null; sudo jq -c 'select(.verb=="create" and .objectRef.name=="essai-ordre-2") | {stage, level, corps: .requestObject.data}' /tmp/essai-audit/audit.log
```

```text
API server de test prêt
{"stage":"ResponseComplete","level":"RequestResponse","corps":{"cle":"valeur"}}
```

Cette fois, `RequestResponse`, un seul événement, et le corps de la requête
(`cle: valeur`) est dans le journal. La règle précise d'abord, la règle
générale à la fin : c'est l'erreur la plus fréquente dans une politique
d'audit, et elle ne produit aucun message d'erreur.

## 🎭 Exercice 3 : une action faite sous une autre identité

`kubectl --as` permet d'agir au nom d'un autre utilisateur, si l'on en a le
droit. Supprimez la première ConfigMap au nom de `alice`, puis cherchez qui
l'a supprimée :

```bash
kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt delete configmap essai-ordre --as=alice > /dev/null; sudo jq -c 'select(.verb=="delete" and .objectRef.name=="essai-ordre") | {qui: .user.username, pour: .impersonatedUser.username, verb, objet: .objectRef.name, quand: .requestReceivedTimestamp}' /tmp/essai-audit/audit.log
```

```text
{"qui":"kubernetes-admin","pour":"alice","verb":"delete","objet":"essai-ordre","quand":"2026-11-22T10:57:53.827115Z"}
```

Le journal garde les deux identités : `kubernetes-admin` a fait la requête,
au nom d'`alice` (`impersonatedUser`), avec l'heure exacte. Une investigation
qui ne regarderait que `impersonatedUser` accuserait `alice` à tort : c'est
`user` qui dit qui a réellement agi.

## 🧹 Nettoyage

Arrêtez le serveur d'essai, effacez ses données du préfixe `/essai-audit`
d'etcd, puis son dossier :

```bash
sudo kill $(sudo cat /tmp/essai-audit/pid); sleep 3; sudo kubectl --kubeconfig /etc/kubernetes/admin.conf -n kube-system exec etcd-k8s-cp.lab -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key del --prefix /essai-audit; sudo rm -rf /tmp/essai-audit; ls -d /tmp/essai-audit
```

```text
56
ls: cannot access '/tmp/essai-audit': No such file or directory
```

`etcdctl` a effacé les clés du préfixe d'essai (le nombre affiché), et le
dossier n'existe plus. L'API server du cluster n'a jamais été modifié.

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-audit-log-policy
dsoxlab check cks-audit-log-policy
```

```text
╭─ Résultat : cks-audit-log-policy ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/7 tests  │
╰───────────────────────────────────╯
```

0 sur 7 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : donner à l'API server du cluster une politique qui
enregistre les accès aux Secrets en entier et le reste en métadonnées, sans
qu'il cesse de répondre.

```bash
dsoxlab run cks-audit-log-policy
dsoxlab challenge cks-audit-log-policy
```
