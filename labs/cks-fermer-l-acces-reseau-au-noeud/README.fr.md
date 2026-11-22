# Fermer l'accès réseau à un worker sans couper le cluster

La leçon montre comment écrire une table nftables en politique `drop` qui ne
laisse passer que les flux de Kubernetes. Ce cours ajoute ce qu'il faut faire
**avant** de la charger : voir les tables que kube-proxy et Calico ont déjà
posées, faire refuser une règle mal écrite, et **compter** le trafic qui
arrive sur un port sans rien bloquer, pour savoir quoi laisser ouvert.

Vous travaillez sur `k8s-w1.lab`, par `ssh` depuis le control plane. La table
d'essai de ce cours **compte** les paquets, elle n'en jette aucun : vous ne
risquez pas de couper le nœud. Le challenge porte sur un autre nœud : vous le
ferez seul, à la fin.

Page associée : [Durcir les nœuds d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-fermer-l-acces-reseau-au-noeud
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et `ssh` atteint les
workers.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2, Ubuntu 24.04 et nftables 1.0.9.

## 🗂️ Exercice 1 : ce qui est déjà en place

Un nœud Kubernetes n'est jamais vierge côté pare-feu. Listez les tables
nftables de `k8s-w1.lab` :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft list tables'
```

```text
table ip mangle
table ip filter
table ip6 mangle
table ip nat
table ip6 nat
table ip6 filter
table ip raw
table arp calico-arp
```

Aucune de ces tables n'est à vous : les tables `ip` et `ip6` viennent de
kube-proxy (qui écrit par `iptables`, lui-même branché sur nftables), et
`calico-arp` vient de Calico. Comptez les règles qu'ils y ont posées :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo iptables-save 2>/dev/null | grep -c -E "^-A (KUBE|cali)"; echo "(règles kube-proxy et Calico vues par iptables)"'
```

```text
202
(règles kube-proxy et Calico vues par iptables)
```

Ces règles font fonctionner les Services et le réseau des Pods. C'est pour
cela que votre pare-feu vit dans **sa propre table** de la famille `inet`, et
qu'on ne vide jamais tout le jeu de règles (`flush ruleset`) sur un nœud.

## ✅ Exercice 2 : vérifier une règle avant de la charger

Écrivez une table d'essai qui ne jette rien (`policy accept`) mais **compte**
les paquets qui arrivent sur trois ports : SSH (22), le kubelet (10250) et la
santé de kube-proxy (10256). `nft -c` la vérifie sans la charger :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'cat > /tmp/essai-comptage.nft <<"NFT"
table inet essai_comptage {
  chain entree {
    type filter hook input priority 10; policy accept;
    tcp dport 22 counter
    tcp dport 10250 counter
    tcp dport 10256 counter
  }
}
NFT
sudo nft -c -f /tmp/essai-comptage.nft; echo "vérification : code $?"'
```

```text
vérification : code 0
```

Le code 0 dit que le fichier est valide. Faites maintenant une faute de frappe
dans la politique, et vérifiez de nouveau :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sed "s/policy accept;/policy acept;/" /tmp/essai-comptage.nft > /tmp/essai-faute.nft; sudo nft -c -f /tmp/essai-faute.nft 2>&1 | head -3'
```

```text
/tmp/essai-faute.nft:3:48-52: Error: syntax error, unexpected string, expecting accept or drop or '$'
    type filter hook input priority 10; policy acept;
                                               ^^^^^
```

`nft` indique la ligne, la colonne, et ce qu'il attendait (`accept or drop`).
Rien n'a été chargé : c'est tout l'intérêt de `-c` sur une machine où une
règle fausse peut vous couper l'accès.

## 📊 Exercice 3 : compter ce qui arrive

Chargez la table d'essai, provoquez un appel de l'API server vers le kubelet
de `k8s-w1.lab` (un `kubectl logs` sur un Pod qui y tourne), puis lisez les
compteurs :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft -f /tmp/essai-comptage.nft'; P=$(kubectl -n kube-system get pods -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-w1.lab -o name); kubectl -n kube-system logs $P --tail=1 >/dev/null; echo "kubectl logs sur $P : code $?"; ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft list table inet essai_comptage | grep counter'
```

```text
kubectl logs sur pod/kube-proxy-pcbrz : code 0
		tcp dport 22 counter packets 21 bytes 4935
		tcp dport 10250 counter packets 7 bytes 3236
		tcp dport 10256 counter packets 0 bytes 0
```

Le port 22 compte votre propre session SSH. Le port 10250 compte le `kubectl
logs` : l'API server ne lit pas les journaux lui-même, il les demande au
kubelet du nœud sur ce port. Le port 10256 reste à 0 : personne n'interroge la
santé de kube-proxy dans ce cluster. Ces compteurs, relevés sur une vraie
journée de travail, vous disent quels ports une politique `drop` doit laisser
ouverts, et depuis où.

## 🧽 Exercice 4 : retirer sa seule table

Supprimez la table d'essai, et seulement elle :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft delete table inet essai_comptage; sudo nft list tables; rm -f /tmp/essai-comptage.nft /tmp/essai-faute.nft'
```

```text
table ip mangle
table ip filter
table ip6 mangle
table ip nat
table ip6 nat
table ip6 filter
table ip raw
table arp calico-arp
```

Les tables de kube-proxy et de Calico sont toutes là, intactes : `nft delete
table inet essai_comptage` ne touche que la vôtre. Vérifiez que le nœud va
bien :

```bash
kubectl get node k8s-w1.lab
```

```text
NAME         STATUS   ROLES    AGE   VERSION
k8s-w1.lab   Ready    <none>   22h   v1.37.2
```

## 🧹 Nettoyage

L'exercice 4 a déjà retiré la table et les fichiers d'essai : il ne reste rien
sur `k8s-w1.lab`.

Quittez la machine et remettez le lab à zéro. `dsoxlab reset` rejoue le
nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-fermer-l-acces-reseau-au-noeud
dsoxlab check cks-fermer-l-acces-reseau-au-noeud
```

```text
╭─ Résultat : cks-fermer-l-acces-reseau-au-noeud ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                │
╰─────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un worker sans aucun pare-feu, à fermer par une
politique `drop` qui laisse passer les flux du cluster et survit au
redémarrage.

```bash
dsoxlab run cks-fermer-l-acces-reseau-au-noeud
dsoxlab challenge cks-fermer-l-acces-reseau-au-noeud
```
