# Relier deux clusters avec ClusterMesh

La leçon prépare deux clusters Cilium, les relie avec ClusterMesh et rend un
Service global, servi par les deux. Relier les clusters et rendre le Service
global, c'est le challenge du lab : ce cours ne relie rien. Il vérifie les
conditions que la leçon pose sans les contrôler, avant la liaison : des
identités distinctes, des plages de Pods qui ne se recoupent pas, une même
autorité de certification, un point d'entrée joignable et signé par cette
autorité, et l'état que rapporte la CLI avant toute liaison.

Vous travaillez dans un répertoire d'essai, `~/essai-mesh`, sans rien créer
dans les clusters. Le challenge porte sur la liaison et sur le Service
`echo` : vous le ferez seul, à la fin.

Page associée : [Relier deux clusters avec ClusterMesh](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/clustermesh/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-relier-deux-clusters
```

Vous êtes maintenant connecté à `ha-cp1.lab`, le nœud unique de
`cluster-1`. Votre kubeconfig connaît les deux clusters, chacun par son
contexte :

```bash
kubectl config get-contexts
```

```text
CURRENT   NAME        CLUSTER         AUTHINFO          NAMESPACE
*         cluster-1   k8s-cluster-1   admin-cluster-1
          cluster-2   k8s-cluster-2   admin-cluster-2
```

Toutes les commandes de ce cours passent `--context`, pour qu'aucun doute ne
reste sur le cluster interrogé. Les sorties montrées ont été relevées sur ces
machines le 22 novembre 2026 (Kubernetes v1.37.2, Cilium 1.20.5, CLI `cilium`
v0.20.3).

## 🪪 Exercice 1 : deux identités distinctes

Chaque cluster d'un maillage doit porter un nom et un identifiant numérique
qui lui sont propres : Cilium s'en sert pour savoir à quel cluster appartient
chaque Pod et chaque identité de sécurité. Lisez-les dans la configuration de
Cilium de chaque cluster :

```bash
for c in cluster-1 cluster-2; do echo "$c: $(kubectl --context $c -n kube-system get cm cilium-config -o jsonpath='{.data.cluster-name} id={.data.cluster-id}')"; done
```

```text
cluster-1: cluster-1 id=1
cluster-2: cluster-2 id=2
```

Noms et identifiants diffèrent. Ces valeurs se fixent à l'installation de
Cilium : deux clusters installés avec les valeurs par défaut porteraient le
même nom, `default`, et le même identifiant, et ne pourraient pas être reliés
tels quels.

## 🗺️ Exercice 2 : des plages de Pods qui ne se recoupent pas

Un Pod de `cluster-1` doit pouvoir joindre un Pod de `cluster-2` par son
adresse : deux Pods ne doivent donc jamais avoir la même. Lisez le bloc de
chaque nœud, puis vérifiez que les deux pools ne se recoupent pas. Les pools,
`10.241.0.0/16` et `10.242.0.0/16`, sont ceux de la clé
`cluster-pool-ipv4-cidr` de `cilium-config` :

```bash
for c in cluster-1 cluster-2; do echo "$c: $(kubectl --context $c get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name} {.spec.ipam.podCIDRs}{end}')"; done
python3 -c 'import ipaddress as ip; print("recoupement :", ip.ip_network("10.241.0.0/16").overlaps(ip.ip_network("10.242.0.0/16")))'
```

```text
cluster-1: ha-cp1.lab ["10.241.0.0/24"]
cluster-2: ha-cp2.lab ["10.242.0.0/24"]
recoupement : False
```

Chaque nœud a son bloc dans le pool de son cluster, et les pools ne se
recoupent pas. Deux clusters installés avec le pool par défaut de Cilium,
`10.0.0.0/8`, auraient le même : deux Pods, un de chaque côté, pourraient
recevoir la même adresse.

## 🔐 Exercice 3 : une même autorité de certification

Les agents d'un cluster se connectent au point d'entrée de l'autre en TLS.
Ils ne lui font confiance que si son certificat est signé par l'autorité
qu'ils connaissent. Les deux clusters doivent donc partager l'autorité de
certification de Cilium, le Secret `cilium-ca`. Gardez celle de `cluster-1`
dans le répertoire d'essai pour l'exercice suivant, puis comparez les
empreintes des deux :

```bash
mkdir -p ~/essai-mesh
kubectl --context cluster-1 -n kube-system get secret cilium-ca -o jsonpath='{.data.ca\.crt}' | base64 -d > ~/essai-mesh/ca-cluster-1.crt
for c in cluster-1 cluster-2; do echo "$c: $(kubectl --context $c -n kube-system get secret cilium-ca -o jsonpath='{.data.ca\.crt}' | base64 -d | openssl x509 -noout -fingerprint -sha256 | cut -c1-60)"; done
```

```text
cluster-1: sha256 Fingerprint=38:4E:B6:1D:33:AA:55:CC:76:E8:1F:3A:BD:AA
cluster-2: sha256 Fingerprint=38:4E:B6:1D:33:AA:55:CC:76:E8:1F:3A:BD:AA
```

Les empreintes sont identiques (le début suffit à la comparaison) : les deux
clusters ont la même autorité. Deux clusters installés chacun de son côté en
auraient chacun une, générée à l'installation.

## 🔌 Exercice 4 : un point d'entrée joignable et signé

Chaque cluster expose son `clustermesh-apiserver`, le point d'entrée que les
agents de l'autre cluster interrogent. Ici, c'est un Service NodePort. Lisez
celui de `cluster-2`, testez son port depuis `ha-cp1`, puis un port voisin où
rien n'écoute :

```bash
kubectl --context cluster-2 -n kube-system get svc clustermesh-apiserver
timeout 3 bash -c '</dev/tcp/10.10.50.19/32379'; echo "32379 code=$?"
timeout 3 bash -c '</dev/tcp/10.10.50.19/32380'; echo "32380 code=$?"
```

```text
NAME                    TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
clustermesh-apiserver   NodePort   10.112.253.96   <none>        2379:32379/TCP   2m5s
32379 code=0
bash: connect: Connection refused
bash: line 1: /dev/tcp/10.10.50.19/32380: Connection refused
32380 code=1
```

Le port `32379` de `ha-cp2` (`10.10.50.19`) accepte la connexion, le port
voisin la refuse. Joignable ne veut pas encore dire digne de confiance.
Demandez à `openssl` de vérifier le certificat présenté par ce point
d'entrée avec l'autorité de `cluster-1` :

```bash
openssl s_client -connect 10.10.50.19:32379 -CAfile ~/essai-mesh/ca-cluster-1.crt </dev/null 2>/dev/null | grep -E '^(subject|issuer)=|Verify return code'
```

```text
subject=CN = clustermesh-apiserver.kube-system.svc
issuer=CN = Cilium CA
Verify return code: 0 (ok)
```

Le point d'entrée de `cluster-2` présente un certificat émis par `Cilium CA`,
et `openssl` le valide avec l'autorité de `cluster-1` : `Verify return code:
0 (ok)`. C'est exactement la vérification que feront les agents de
`cluster-1` une fois les clusters reliés. Avec deux autorités différentes,
vous liriez ici un code de vérification non nul.

## 📋 Exercice 5 : l'état avant la liaison

La CLI `cilium` résume l'état du maillage d'un cluster. Son affichage par
défaut est fait pour l'œil ; pour un script, demandez du JSON (`-o json`) et
gardez les champs utiles avec `jq`. Les lignes de progression partent sur la
sortie d'erreur, que `2>/dev/null` écarte :

```bash
cilium clustermesh status --context cluster-1 -o json 2>/dev/null | jq -c '{cluster: .access_information.cluster_name, adresse: .access_information.service_ips, port: .access_information.service_port, connectes: .connectivity.connected}'; echo "code=$?"
```

```text
{"cluster":"cluster-1","adresse":["10.10.50.18"],"port":32379,"connectes":{}}
code=0
```

Le point d'entrée de `cluster-1` est annoncé à l'adresse de `ha-cp1`,
`10.10.50.18`, sur le port `32379` : c'est l'adresse que l'autre cluster
utilisera. Le champ qui compte est `connectes`, un objet vide : aucun cluster
n'est relié. La commande sort pourtant en **0** : un script ne peut pas
s'appuyer sur le code de sortie pour savoir si les clusters sont reliés, il
doit lire ce champ. L'adresse annoncée est celle d'un nœud, puisque le
Service est un NodePort : si ce nœud disparaît, l'autre cluster perd son
point d'entrée.

## 🧹 Nettoyage

Supprimez le répertoire d'essai, la seule chose que ce cours a créée :

```bash
rm -rf ~/essai-mesh; ls -d ~/essai-mesh
```

```text
ls: cannot access '/home/ansible/essai-mesh': No such file or directory
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-relier-deux-clusters
dsoxlab check k8s-relier-deux-clusters
```

```text
╭─ Résultat : k8s-relier-deux-clusters ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests      │
╰───────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : relier les deux clusters, rendre leur Service
`echo` global, et prouver qu'un client de `cluster-1` reçoit des réponses des
deux clusters.

```bash
dsoxlab run k8s-relier-deux-clusters
dsoxlab challenge k8s-relier-deux-clusters
```
